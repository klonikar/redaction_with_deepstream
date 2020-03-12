#!/usr/bin/env python3

# export PYTHONPATH=$HOME/projects/deepstream_sdk_v4.0.2_jetson/sources/python/bindings/jetson

import os
import os.path
import sys
#sys.path.append('../')
import argparse
import traceback
import pdb
import time
import json
import base64
#from _gst_nvds_bindings import ffi, lib
import gi
#gi.require_version('Gtk', '3.0')
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject #, Gtk
import pyds

NVDS_META_STRING = b"nvdsmeta"
GST_META_TAG_NVSTREAM = b"nvstream"
GST_CAPS_FEATURE_META_GST_NVSTREAM_META = b"meta:GstNvStreamMeta"

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

class Redaction_Main(object):
    """Class to initialize the deepstream redaction example pipeline"""
    def __init__(self, args):
        super(Redaction_Main, self).__init__()
        self.args = args
        self.pgie_classes_str = ["face", "license_plate", "make", "model"]
        self.frame_number = 0
        #self.statePtr = ffi.new("void **");
        #self._nvdsmeta_quark = lib.g_quark_from_static_string(NVDS_META_STRING)
        # Create gstreamer loop
        self.loop = GObject.MainLoop()
        # Create gstreamer pipeline
        self.pipeline = Gst.Pipeline.new("ds-redaction-pipeline")
        # Create components for decoding the input source
        if args.input_mp4:
            self.source = Gst.ElementFactory.make("filesrc", "file-source")
            self.source.set_property("location", args.input_mp4)
            self.decoder = Gst.ElementFactory.make("decodebin", "decoder")
            self.decoder.connect("pad-added", self.cb_newpad, self)
            self.pipeline.add(self.source)
            self.pipeline.add(self.decoder) # add decode bin into the pipeline
            self.source.link(self.decoder)
        else:
            self.source = Gst.ElementFactory.make("v4l2src", "camera-source")
            self.source.set_property("device", "/dev/video0")
            self.vidconv_src = Gst.ElementFactory.make("videoconvert", "vidconv_src")
            self.nvvidconv_src = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv_src")
            self.filter_src = Gst.ElementFactory.make("capsfilter", "filter_src")
            self.nvvidconv_src.set_property("nvbuf-memory-type", 0)
            caps_filter_src = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12, width=1280, height=720, framerate=30/1")
            self.filter_src.set_property("caps", caps_filter_src)
            self.pipeline.add(self.source)
            self.pipeline.add(self.vidconv_src)
            self.pipeline.add(self.nvvidconv_src)
            self.pipeline.add(self.filter_src)
            self.source.link(self.vidconv_src)
            self.vidconv_src.link(self.nvvidconv_src)
            self.nvvidconv_src.link(self.filter_src)
            # caps_filter_src.unref() or gst_caps_unref
        # Create main processing bin
        self.video_full_processing_bin = Gst.Bin.new("video-process-bin")
        self.streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
        self.streammux.set_property("width", 1280)
        self.streammux.set_property("height", 720)
        self.streammux.set_property("batch-size", 1)
        self.streammux.set_property("batched-push-timeout", 40000)
        self.streammux.set_property("nvbuf-memory-type", 0)

        pad_name_sink = "sink_0"
        self.videopad = self.streammux.get_request_pad(pad_name_sink)

        # Use nvinfer to run inferencing on decoder's output,
        # behaviour of inferencing is set through config file.
        # Create components for the detection
        self.queue_pgie = Gst.ElementFactory.make("queue", "queue_pgie")
        self.pgie = Gst.ElementFactory.make("nvinfer", "primary-nvinference-engine")
        self.pgie.set_property("config-file-path", args.pgie_config)
        #self.videopad = self.queue_pgie.get_static_pad("sink")

        # Use nvosd to render bbox/text on top of the input video.
        # Create components for the rendering
        self.nvvidconv_osd = Gst.ElementFactory.make ("nvvideoconvert", "nvvidconv_osd")
        self.osd = Gst.ElementFactory.make("nvdsosd", "nv-onscreendisplay")

        #self.queue_osd = Gst.ElementFactory.make("queue", "queue_osd")

        #self.filter_osd = Gst.ElementFactory.make("capsfilter", "filter_osd")
        #caps_filter_osd = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
        #self.filter_osd.set_property("caps", caps_filter_osd)
        # caps_filter_osd.unref() or gst_caps_unref
        # self.osd.set_property("gpu-id", 0)
        # Create components for the output
        if args.output_mp4 is not None:
            # If output file is set, then create components for encoding and exporting to mp4 file
            print("Sending output to ", args.output_mp4)
            self.queue_sink = Gst.ElementFactory.make("queue", "queue_sink")
            self.nvvidconv_sink = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv_sink")
            self.filter_sink = Gst.ElementFactory.make("capsfilter", "filter_sink")
            caps_filter_sink = Gst.Caps.from_string("video/x-raw, format=I420")
            self.filter_sink.set_property("caps", caps_filter_sink)
            # caps_filter_sink.unref() or gst_caps_unref
            self.videoconvert = Gst.ElementFactory.make("videoconvert", "videoconverter")
            self.encoder = Gst.ElementFactory.make("avenc_mpeg4", "mp4-encoder")
            self.encoder.set_property("bitrate", 1000000)
            self.muxer = Gst.ElementFactory.make("qtmux", "muxer")
            self.sink = Gst.ElementFactory.make("filesink", "nvvideo-renderer")
            self.sink.set_property("location", args.output_mp4)
        else:
            if os.uname().machine == 'aarch64': # PLATFORM_TEGRA
                self.transform = Gst.ElementFactory.make("nvegltransform", "nvegl-transform")
                if self.transform is None:
                    print("One tegra element could not be created. Exiting.")
                    return

                self.sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
                self.sink.set_property("sync", False)
                self.sink.set_property("max-lateness", -1)
                self.sink.set_property("async", False)
                self.sink.set_property("qos", True)
            else:
                self.sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
                self.sink.set_property("sync", False)
                self.sink.set_property("max-lateness", -1)
                self.sink.set_property("async", False)
                self.sink.set_property("qos", True)
                if args.input_mp4:
                    self.sink.set_property("sync", True)


        # Check all components
        if self.pipeline is None:
            print("pipeline could not be created. Exiting.")
            return
        if self.source is None:
            print("source could not be created. Exiting.")
            return
        if args.input_mp4 is not None and self.decoder is None:
            print("decoder could not be created. Exiting.")
            return
        if self.video_full_processing_bin is None:
            print("video_full_processing_bin could not be created. Exiting.")
            return
        if self.queue_pgie is None:
            print("queue_pgie could not be created. Exiting.")
            return
        if self.pgie is None:
            print("pgie could not be created. Exiting.")
            return
        if args.output_mp4 is not None and self.queue_sink is None:
            print("queue_sink could not be created. Exiting.")
            return
        if self.nvvidconv_osd is None:
            print("nvvidconv_osd could not be created. Exiting.")
            return
        if args.input_mp4 is None and self.filter_src is None:
            print("filter_src could not be created. Exiting.")
            return
        if self.osd is None:
            print("osd could not be created. Exiting.")
            return
        if self.sink is None:
            print("sink could not be created. Exiting.")
            return


        # we add a message handler
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        self.bus_watch_id = bus.connect ("message", self.bus_call, self.loop)
        bus.unref() #Gst.Object.unref(bus)
        # Set up the pipeline
        
        # Set up the video_full_processing_bin
        # add all the elements to the bin
        self.video_full_processing_bin.add(self.streammux)
        self.video_full_processing_bin.add(self.queue_pgie)
        self.video_full_processing_bin.add(self.pgie)
        self.video_full_processing_bin.add(self.nvvidconv_osd)
        #self.video_full_processing_bin.add(self.filter_osd)
        self.video_full_processing_bin.add(self.osd)
        # link the elements together
        self.streammux.link(self.queue_pgie)
        self.queue_pgie.link(self.pgie)
        self.pgie.link(self.nvvidconv_osd)
        #self.nvvidconv_osd.link(self.filter_osd)
        #self.filter_osd.link(self.osd)
        self.nvvidconv_osd.link(self.osd)

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

        # link soure and video_full_processing_bin
        if args.input_mp4 is None:
            sinkpad = self.video_full_processing_bin.get_static_pad("sink")
            if sinkpad is None:
                print("video_full_processing_bin request sink pad failed. Exiting.")
                return
            srcpad = self.filter_src.get_static_pad("src")
            if srcpad is None:
                print("filter_src request src pad failed. Exiting.")
                return
            if srcpad.link(sinkpad) != Gst.PadLinkReturn.OK:
                print("Failed to link pads. Exiting.")
                return
            sinkpad.unref()
            srcpad.unref()
        if args.output_mp4:
            self.video_full_processing_bin.add(self.queue_sink)
            self.video_full_processing_bin.add(self.nvvidconv_sink)
            self.video_full_processing_bin.add(self.filter_sink)
            self.video_full_processing_bin.add(self.videoconvert)
            self.video_full_processing_bin.add(self.encoder)
            self.video_full_processing_bin.add(self.muxer)
            self.video_full_processing_bin.add(self.sink)
            self.osd.link(self.queue_sink)
            self.queue_sink.link(self.nvvidconv_sink)
            self.nvvidconv_sink.link(self.filter_sink)
            self.filter_sink.link(self.videoconvert)
            self.videoconvert.link(self.encoder)
            self.encoder.link(self.muxer)
            self.muxer.link(self.sink)
        else:
            if os.uname().machine == 'aarch64': # PLATFORM_TEGRA
                self.video_full_processing_bin.add(self.transform)
                self.video_full_processing_bin.add(self.sink)
                self.osd.link(self.transform)
                self.transform.link(self.sink)
            else:
                self.video_full_processing_bin.add(self.sink)
                self.osd.link(self.sink)

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
        if args.input_mp4:
            print("Now playing: ", args.input_mp4)
        else:
            print("Now playing from webcam")

        self.start = time.time()
        self.pipeline.set_state(Gst.State.PLAYING)

        try:
            self.loop.run()
            #GST_DEBUG_BIN_TO_DOT_FILE_WITH_TS (GST_BIN (pipeline), GST_DEBUG_GRAPH_SHOW_ALL, "ds-app-playing");
        except:
            traceback.print_exc()
        # Out of the main loop, clean up nicely
        self.end = computeDiffInMillis(self.start, time.time())
        print ("Returned, stopping playback, time to execute:", str(self.end), "ms")
        self.pipeline.set_state(Gst.State.NULL)
        #self.osd_sink_pad.remove_probe(self.osd_probe_id)
        print ("Deleting pipeline")
        self.pipeline.unref()
        # GObject.Source.remove(self.bus_watch_id)
        self.loop.unref()

    def osd_sink_pad_buffer_probe(self, pad, info, u_data):
        print("sink pad probe invoked", "pad", pad, "info", info, "info.data", hex(info.data), "hash of get_buffer", hex(hash(info.get_buffer())), "info.get_buffer", info.get_buffer(), "u_data", u_data, "self", self)
        #pdb.set_trace()
        #Intiallizing object counter with 0.
        obj_counter = {
            PGIE_CLASS_ID_VEHICLE:0,
            PGIE_CLASS_ID_PERSON:0,
            PGIE_CLASS_ID_BICYCLE:0,
            PGIE_CLASS_ID_ROADSIGN:0
        }
        num_rects=0

        gst_buffer = info.get_buffer()
        if not gst_buffer:
            print("Unable to get GstBuffer ")
            return

        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
        bbox_params_dump_file = None
        #batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(info.data)
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.glist_get_nvds_frame_meta()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
            except StopIteration:
                print("NvDS Meta contained NULL meta")
                break
            if self.args.output_kitti is not None:
                bbox_file = "%s/%06d.txt" % (self.args.output_kitti, self.frame_number)
                bbox_params_dump_file = open(bbox_file, "w")
            batch_frame_number = frame_meta.frame_num
            num_rects = frame_meta.num_obj_meta
            l_obj = frame_meta.obj_meta_list
            while l_obj is not None:
                try:
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta = pyds.glist_get_nvds_object_meta(l_obj.data)
                except StopIteration:
                    print("NvDsObjectMeta Meta contained NULL meta")
                    break
                obj_counter[obj_meta.class_id] += 1
                rect_params = obj_meta.rect_params
                text_params = obj_meta.text_params
                if text_params.display_text is not None:
                    text_params.set_bg_clr = 0
                    text_params.font_params.font_size = 0

                # Draw black patch to cover license plates (class_id = 1)
                if obj_meta.class_id == 1:
                    rect_params.border_width = 0
                    rect_params.has_bg_color = 1
                    rect_params.bg_color.set(0.5, 0.0, 0.5, 1.0)
                    #rect_params.bg_color.red = 0.0
                    #rect_params.bg_color.green = 0.0
                    #rect_params.bg_color.blue = 0.0
                    #rect_params.bg_color.alpha = 1.0
                # Draw skin-color patch to cover faces (class_id = 0)
                if obj_meta.class_id == 0:
                    rect_params.border_width = 0
                    rect_params.has_bg_color = 1
                    rect_params.bg_color.set(0.92, 0.75, 0.56, 1.0)
                    #rect_params.bg_color.red = 0.92
                    #rect_params.bg_color.green = 0.75
                    #rect_params.bg_color.blue = 0.56
                    #rect_params.bg_color.alpha = 1.0
                if bbox_params_dump_file is not None:
                    left = rect_params.left
                    top = rect_params.top
                    right = left + rect_params.width
                    bottom = top + rect_params.height
                    class_index = obj_meta.class_id
                    text = self.pgie_classes_str[obj_meta.class_id]
                    bbox_params_dump_file.write("%s 0.0 0 0.0 %d.00 %d.00 %d.00 %d.00 0.0 0.0 0.0 0.0 0.0 0.0 0.0\n" % (text, left, top, right, bottom))

                try: 
                    l_obj = l_obj.next
                except StopIteration:
                    print("NvDsObjectMeta next contained NULL meta")
                    break
            if bbox_params_dump_file is not None:
                bbox_params_dump_file.close()
                bbox_params_dump_file = None
            try:
                l_frame = l_frame.next
            except StopIteration:
                break

        """
        buf = ffi.cast("void *", info.data)
        gst_meta = lib.gst_buffer_iterate_meta(buf, self.statePtr)
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
                        text_params = obj_meta.text_params
                        if text_params.display_text != ffi.NULL:
                            lib.g_free(text_params.display_text)

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
        """
        self.frame_number += 1
        return Gst.PadProbeReturn.OK

    def bus_call(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.end = computeDiffInMillis(self.start, time.time())
            print("End-of-stream\n")
            self.pipeline.set_state(Gst.State.NULL)
            self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write("Error: %s: %s\n" % (err, debug))
            self.pipeline.set_state(Gst.State.NULL)
            self.loop.quit()
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            if isinstance(message.src, Gst.Pipeline):
                if new_state == Gst.State.PLAYING:
                    self.start = time.time()
                    print("Pipeline running")
                    #GST_DEBUG_BIN_TO_DOT_FILE_WITH_TS (GST_BIN (pipeline), GST_DEBUG_GRAPH_SHOW_ALL, "ds-app-playing")
                elif new_state == Gst.State.PAUSED:
                    if old_state == Gst.State.PLAYING:
                        print("Pipeline paused")
                elif new_state == Gst.State.READY:
                    if old_state == Gst.State.NULL:
                        print("Pipeline ready")
                    else:
                        print("Pipeline stopped")

        return True

    """
    The callback function is called when the decoder_bin establishes video source from the input mp4 file,
    then connects the src pad to the following video_full_processing_bin.
    The connection is dynamic.
    """
    def cb_newpad(self, decodebin, pad, data):
        # only link once
        # videopad = self.video_full_processing_bin.get_static_pad("sink")
        print("New pad event captured for sinkpad...")
        if self.video_full_processing_bin_sink_pad.is_linked():
            print("sinkpad already linked...")
            # videopad.unref()
            return;
        # check media type
        caps = pad.query_caps(None)
        capsStr = caps.get_structure(0)
        print("pad caps", capsStr.get_name())
        if capsStr.get_name().find("video") < 0:
            print("caps", capsStr.get_name(), " does not have video")
            # caps.unref()
            return;

        # caps.unref()
        # link'n'play
        # pad.link(videopad)
        pad.link(self.video_full_processing_bin_sink_pad)
        # videopad.unref()

def computeDiffInMillis(start, end):
    return int(1000*(end-start))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="script to run image redaction")
    parser.add_argument('-c', '--pgie_config', default = "pgie_config_fd_lpd.txt", help='(required) configuration file for the nvinfer detector (primary gie)')
    parser.add_argument('-i', '--input_mp4', help='(required) path to input mp4 file')
    parser.add_argument('-o', '--output_mp4', help='(optional) path to output mp4 file. If this is unset then on-screen display will be used')
    parser.add_argument('-k', '--output_kitti', help = "(optional) path to the folder for containing output kitti files. If this is unset or the path does not exist then app won't output kitti files")

    args = parser.parse_args()

    # Check input arguments
    if args.pgie_config is None:
        parser.print_help()
        exit(1)

    GObject.threads_init()
    Gst.init(None) # sys.argv
    Redaction_Main(args)
