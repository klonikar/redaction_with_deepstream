#!/usr/bin/env python3

import os
import os.path
import sys
import argparse
import traceback
import pdb
import json
import base64
from _gst_nvds_bindings import ffi, lib
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject, Gtk

NVDS_META_STRING = b"nvdsmeta"

class Redaction_Main(object):
    """Class to initialize the deepstream redaction example pipeline"""
    def __init__(self, args):
        super(Redaction_Main, self).__init__()
        self.args = args
        self.pgie_classes_str = ["face", "license_plate", "make", "model"]
        self.frame_number = 0
        self.statePtr = ffi.new("void **");
        self._nvdsmeta_quark = lib.g_quark_from_static_string(NVDS_META_STRING)
        # Create gstreamer loop
        self.loop = GObject.MainLoop()
        # Create gstreamer pipeline
        self.pipeline = Gst.Pipeline.new("ds-redaction-pipeline")
        # Create components for decoding the input mp4 file
        self.source = Gst.ElementFactory.make("filesrc", "file-source")
        self.source.set_property("location", args.input_mp4)
        self.decoder = Gst.ElementFactory.make("decodebin", "decoder")
        self.decoder.connect("pad-added", self.cb_newpad, self)
        # Create main processing bin
        self.video_full_processing_bin = Gst.Bin.new("video-process-bin")
        # Use nvinfer to run inferencing on decoder's output,
        # behaviour of inferencing is set through config file.
        # Create components for the detection
        self.queue_pgie = Gst.ElementFactory.make("queue", "queue_pgie")
        self.pgie = Gst.ElementFactory.make("nvinfer", "primary-nvinference-engine")
        self.pgie.set_property("config-file-path", args.pgie_config)
        self.videopad = self.queue_pgie.get_static_pad("sink")

        # Use nvosd to render bbox/text on top of the input video.
        # Create components for the rendering
        self.queue_osd = Gst.ElementFactory.make("queue", "queue_osd")
        self.nvvidconv_osd = Gst.ElementFactory.make("nvvidconv", "nvvidconv_osd")
        self.filter_osd = Gst.ElementFactory.make("capsfilter", "filter_osd")
        caps_filter_osd = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
        self.filter_osd.set_property("caps", caps_filter_osd)
        # caps_filter_osd.unref() or gst_caps_unref
        self.osd = Gst.ElementFactory.make("nvosd", "nv-onscreendisplay")
        # self.osd.set_property("gpu-id", 0)
        # Create components for the output
        if args.output_mp4 is not None:
            print("Sending output to ", args.output_mp4)
            self.queue_sink = Gst.ElementFactory.make("queue", "queue_sink")
            self.nvvidconv_sink = Gst.ElementFactory.make("nvvidconv", "nvvidconv_sink")
            self.filter_sink = Gst.ElementFactory.make("capsfilter", "filter_sink")
            caps_filter_sink = Gst.Caps.from_string("video/x-raw, format=RGBA")
            self.filter_sink.set_property("caps", caps_filter_sink)
            # caps_filter_sink.unref() or gst_caps_unref
            self.videoconvert = Gst.ElementFactory.make("videoconvert", "videoconverter")
            self.encoder = Gst.ElementFactory.make("avenc_mpeg4", "mp4-encoder")
            self.encoder.set_property("bitrate", 8000000)
            self.muxer = Gst.ElementFactory.make("qtmux", "muxer")
            self.sink = Gst.ElementFactory.make("filesink", "nvvideo-renderer")
            self.sink.set_property("location", args.output_mp4)
        else:
            self.sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")

        # Check all components
        if self.pipeline is None or self.source is None or self.decoder is None or self.video_full_processing_bin is None or self.queue_pgie is None or self.pgie is None or self.queue_osd is None or self.nvvidconv_osd is None or self.filter_osd is None or self.osd is None or self.sink is None:
            print("One element could not be created. Exiting.")
            return

        # we add a message handler
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        self.bus_watch_id = bus.connect ("message", self.bus_call, self.loop)
        bus.unref() #Gst.Object.unref(bus)
        # Set up the pipeline
        # add decode bin into the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(self.decoder)
        self.source.link(self.decoder)
        # Set up the video_full_processing_bin
        # add all the elements to the bin
        self.video_full_processing_bin.add(self.queue_pgie)
        self.video_full_processing_bin.add(self.pgie)
        self.video_full_processing_bin.add(self.nvvidconv_osd)
        self.video_full_processing_bin.add(self.filter_osd)
        self.video_full_processing_bin.add(self.osd)
        # link the elements together
        self.queue_pgie.link(self.pgie)
        self.pgie.link(self.nvvidconv_osd)
        self.nvvidconv_osd.link(self.filter_osd)
        self.filter_osd.link(self.osd)

        if args.output_mp4 is not None:
            print("Sending output to ", args.output_mp4)
            self.video_full_processing_bin.add(self.queue_sink)
            self.video_full_processing_bin.add(self.nvvidconv_sink)
            self.video_full_processing_bin.add(self.filter_sink)
            self.video_full_processing_bin.add(self.videoconvert)
            self.video_full_processing_bin.add(self.encoder)
            self.video_full_processing_bin.add(self.muxer)
            self.video_full_processing_bin.add(self.sink)
            # link the elements together
            self.osd.link(self.queue_sink)
            self.queue_sink.link(self.nvvidconv_sink)
            self.nvvidconv_sink.link(self.filter_sink)
            self.filter_sink.link(self.videoconvert)
            self.videoconvert.link(self.encoder)
            self.encoder.link(self.muxer)
            self.muxer.link(self.sink)
        else:
            self.video_full_processing_bin.add(self.sink)
            self.osd.link(self.sink)

        # add the video_full_processing_bin into the pipeline
        self.video_full_processing_bin_sink_pad = Gst.GhostPad.new("sink", self.videopad)
        self.video_full_processing_bin.add_pad(self.video_full_processing_bin_sink_pad)
        #Gst.Object.unref(self.videopad)
        self.pipeline.add(self.video_full_processing_bin)
        # add probe to get informed of the meta data generated, we add probe to
        # the sink pad of the osd element, since by that time, the buffer would have
        # had got all the metadata.
        self.osd_sink_pad = self.osd.get_static_pad("sink")
        if self.osd_sink_pad is None:
            print("Unable to get sink pad of osd")
        else:
            print("Adding probe for sink pad of osd")
            self.osd_probe_id = self.osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, self.osd_sink_pad_buffer_probe, None)

        # Set the pipeline to "playing" state
        print("Now playing: ", args.input_mp4)
        self.pipeline.set_state(Gst.State.PLAYING)

        try:
            self.loop.run()
        except:
            traceback.print_exc()
        # Out of the main loop, clean up nicely
        print ("Returned, stopping playback")
        self.pipeline.set_state(Gst.State.NULL)
        #self.osd_sink_pad.remove_probe(self.osd_probe_id)
        print ("Deleting pipeline")
        self.pipeline.unref()
        # GObject.Source.remove(self.bus_watch_id)
        self.loop.unref()

    def osd_sink_pad_buffer_probe(self, pad, info, u_data):
        print("sink pad probe invoked", "pad", pad, "info", info, "info.data", info.get_buffer(), "u_data", u_data, "self", self)
        buf = ffi.cast("void *", info.data)
        gst_meta = lib.gst_buffer_iterate_meta(buf, self.statePtr)
        bbox_params_dump_file = None
        while gst_meta != ffi.NULL:
            print("****got metadata....", gst_meta)
            if lib.gst_meta_has_tag(gst_meta, self._nvdsmeta_quark):
                nvdsmeta = ffi.cast("NvDsMeta *", gst_meta)
                print("*********got deepstream metadata....", nvdsmeta, nvdsmeta.meta_type)
                # We are interested only in intercepting Meta of type
                # "NVDS_META_FRAME_INFO" as they are from our infer elements.
                if nvdsmeta.meta_type == lib.NVDS_META_FRAME_INFO:
                    frame_meta = ffi.cast("NvDsFrameMeta *", nvdsmeta.meta_data)
                    if frame_meta == ffi.NULL:
                        print("NvDS Meta contained NULL meta")
                        self.frame_number += 1
                        return Gst.PadProbeReturn.OK
                    if self.args.output_kitti is not None:
                        bbox_file = "%s/%06d.txt" % (self.args.output_kitti, self.frame_number)
                        bbox_params_dump_file = open(bbox_file, "w")

                    num_rects = frame_meta.num_rects
                    print("num rects", num_rects)
                    # This means we have num_rects in frame_meta->obj_params,
                    # now lets iterate through them
                    for rect_index in range(0, num_rects):
                        # Now using above information we need to form a color patch that should
                        # be displayed on the original video to cover object of interests for redaction purpose
                        obj_meta = frame_meta.obj_params[rect_index]
                        rect_params = obj_meta.rect_params
                        txt_params = obj_meta.text_params
                        if txt_params.display_text != ffi.NULL:
                            lib.g_free(txt_params.display_text)

                        # Draw black patch to cover license plates (class_id = 1)
                        if obj_meta.class_id == 1:
                            rect_params.border_width = 0
                            rect_params.has_bg_color = 1
                            rect_params.bg_color.red = 0.0
                            rect_params.bg_color.green = 0.0
                            rect_params.bg_color.blue = 0.0
                            rect_params.bg_color.alpha = 1.0
                        # Draw skin-color patch to cover faces (class_id = 0)
                        if obj_meta.class_id == 0:
                            rect_params.border_width = 0
                            rect_params.has_bg_color = 1
                            rect_params.bg_color.red = 0.92
                            rect_params.bg_color.green = 0.75
                            rect_params.bg_color.blue = 0.56
                            rect_params.bg_color.alpha = 1.0
                        if bbox_params_dump_file is not None:
                            left = rect_params.left
                            top = rect_params.top
                            right = left + rect_params.width
                            bottom = top + rect_params.height
                            class_index = obj_meta.class_id
                            text = self.pgie_classes_str[obj_meta.class_id]
                            bbox_params_dump_file.write("%s 0.0 0 0.0 %d.00 %d.00 %d.00 %d.00 0.0 0.0 0.0 0.0 0.0 0.0 0.0\n" % (text, left, top, right, bottom))
                    if bbox_params_dump_file is not None:
                        bbox_params_dump_file.close()
                        bbox_params_dump_file = None
            gst_meta = lib.gst_buffer_iterate_meta(buf, self.statePtr)
        self.frame_number += 1
        return Gst.PadProbeReturn.OK

    def bus_call(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("End-of-stream\n")
            self.pipeline.set_state(Gst.State.NULL)
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write("Error: %s: %s\n" % (err, debug))
            self.pipeline.set_state(Gst.State.NULL)
            loop.quit()
        return True

    """
    The callback function is called when the decoder_bin establishes video source from the input mp4 file,
    then connects the src pad to the following video_full_processing_bin.
    The connection is dynamic.
    """
    def cb_newpad(self, decodebin, pad, data):
        # only link once
        # videopad = self.video_full_processing_bin.get_static_pad("sink")
        if self.video_full_processing_bin_sink_pad.is_linked():
            # videopad.unref()
            return;
        # TODO: check media type

        # link and play
        # pad.link(videopad)
        pad.link(self.video_full_processing_bin_sink_pad)
        # videopad.unref()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="script to run image redaction")
    parser.add_argument('-c', '--pgie_config', default = "pgie_config_fd_lpd.txt", help='(required) configuration file for the nvinfer detector (primary gie)')
    parser.add_argument('-i', '--input_mp4', help='(required) path to input mp4 file')
    parser.add_argument('-o', '--output_mp4', help='(optional) path to output mp4 file. If this is unset then on-screen display will be used')
    parser.add_argument('-k', '--output_kitti', help = "(optional) path to the folder for containing output kitti files. If this is unset or the path does not exist then app won't output kitti files")

    args = parser.parse_args()

    # Check input arguments
    if args.input_mp4 is None or args.pgie_config is None:
        parser.print_help()
        exit(1)
    
    GObject.threads_init()
    Gst.init(None) # sys.argv       
    Redaction_Main(args)
