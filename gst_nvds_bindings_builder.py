#!/usr/bin/env python3

from cffi import FFI
ffibuilder = FFI()

ffibuilder.set_source("_gst_nvds_bindings",
  r"""
#include <gst/gst.h>
#include <glib.h>
#include <stdio.h>
#include "gstnvdsmeta.h"
#define MAX_DISPLAY_LEN 64

int gst_meta_has_tag(void *p, int tag) {
   return gst_meta_api_type_has_tag(((GstMeta *)p)->info->api, tag);
}

   """,
  libraries=["gstreamer-1.0", "gobject-2.0", "glib-2.0", "gmodule-2.0" ],
  include_dirs=["../../includes", "/usr/include/gstreamer-1.0", "/usr/lib/x86_64-linux-gnu/gstreamer-1.0/include", "/usr/include/glib-2.0", "/usr/lib/x86_64-linux-gnu/glib-2.0/include"]
  )

ffibuilder.cdef("""
            int g_quark_from_static_string (const char *);
            void *gst_buffer_iterate_meta(void *buf, void **state);
            int gst_meta_has_tag(void *, int tag);
""")

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)

