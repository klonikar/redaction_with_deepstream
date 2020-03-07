/**
 * GstMetaFlags:
 * @GST_META_FLAG_NONE: no flags
 * @GST_META_FLAG_READONLY: metadata should not be modified
 * @GST_META_FLAG_POOLED: metadata is managed by a bufferpool
 * @GST_META_FLAG_LOCKED: metadata should not be removed
 * @GST_META_FLAG_LAST: additional flags can be added starting from this flag.
 *
 * Extra metadata flags.
 */
typedef enum {
  GST_META_FLAG_NONE        = 0,
  GST_META_FLAG_READONLY    = 1, /* (1 << 0), */
  GST_META_FLAG_POOLED      = 2, /* (1 << 1), */
  GST_META_FLAG_LOCKED      = 4, /* (1 << 2), */

  GST_META_FLAG_LAST        = 65536 /* (1 << 16) */
} GstMetaFlags;


/**
 * GstMeta:
 * @flags: extra flags for the metadata
 * @info: pointer to the #GstMetaInfo
 *
 * Base structure for metadata. Custom metadata will put this structure
 * as the first member of their structure.
 */
typedef struct _GstMeta {
  GstMetaFlags       flags;
  const void *info; /* const GstMetaInfo *info; */
} GstMeta;


