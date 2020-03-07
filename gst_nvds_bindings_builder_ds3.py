#!/usr/bin/env python3

# run the following commands to install ffi:
# sudo apt-get install libffi-dev
# sudo sudo pip3 install cffi

from cffi import FFI
ffibuilder = FFI()

ffibuilder.set_source("_gst_nvds_bindings_ds3",
  r"""
#include <gst/gst.h>
#include <glib.h>
#include <stdio.h>
#include "nvdsmetastructs_for_so_ds3.h"
#define MAX_DISPLAY_LEN 64

int gst_meta_has_tag(void *p, int tag) {
   return gst_meta_api_type_has_tag(((GstMeta *)p)->info->api, tag);
}

   """,
  libraries=["gstreamer-1.0", "gobject-2.0", "glib-2.0", "gmodule-2.0" ],
  include_dirs=[".", "/usr/include/gstreamer-1.0", "/usr/lib/x86_64-linux-gnu/gstreamer-1.0/include", "/usr/include/glib-2.0", "/usr/lib/aarch64-linux-gnu/glib-2.0/include", "/usr/lib/x86_64-linux-gnu/glib-2.0/include", "/usr/include/python3.6"]
  )

nvdsStructsDefFile = open("nvdsmetastructs_ds3.h", "r")
nvdsStructsDefs = nvdsStructsDefFile.read()
nvdsStructsDefFile.close()
gstStructsDefFile = open("gstmetastructs.h", "r")
gstStructsDefs = gstStructsDefFile.read()
gstStructsDefFile.close()

ffibuilder.cdef("""
    typedef int gint;
    typedef short gshort;
    typedef int gboolean;
    typedef unsigned long gulong;
    typedef unsigned long guint64;
    typedef double gdouble;
    typedef float gfloat;
    typedef unsigned int guint;
    typedef char gchar;
    typedef void* gpointer;
    typedef guint64 GstClockTime;

    /* functions from gstreamer library */
    int g_quark_from_static_string (const char *);
    void *gst_buffer_iterate_meta(void *buf, void **state);
    void g_free(void *);
    /* new wrapper function around gst_meta_api_type_has_tag library function */
    int gst_meta_has_tag(void *, int tag);
""" + gstStructsDefs + nvdsStructsDefs)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)

