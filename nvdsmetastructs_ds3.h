#define NVDS_MAX_ATTRIBUTES 16
#define NVOSD_MAX_NUM_RECTS 256
/* #define NVDS_META_STRING "nvdsmeta" */
/**
 * Event type flags.
 */
typedef enum NvDsEventType {
  NVDS_EVENT_ENTRY,
  NVDS_EVENT_EXIT,
  NVDS_EVENT_MOVING,
  NVDS_EVENT_STOPPED,
  NVDS_EVENT_EMPTY,
  NVDS_EVENT_PARKED,
  NVDS_EVENT_RESET,
  /** Reserved for future use. Use value greater than this for custom events. */
  NVDS_EVENT_RESERVED = 0x100,
  /** To support custom event */
  NVDS_EVENT_CUSTOM = 0x101,
  NVDS_EVENT_FORCE32 = 0x7FFFFFFF
} NvDsEventType;

/**
 * Object type flags.
 */
typedef enum NvDsObjectType {
  NVDS_OBJECT_TYPE_VEHICLE,
  NVDS_OBJECT_TYPE_PERSON,
  NVDS_OBJECT_TYPE_FACE,
  /** Reserved for future use. Use value greater than this for custom objects. */
  NVDS_OBJECT_TYPE_RESERVED = 0x100,
  /** To support custom object. */
  NVDS_OBJECT_TYPE_CUSTOM = 0x101,
  NVDS_OBEJCT_TYPE_FORCE32 = 0x7FFFFFFF
} NvDsObjectType;

/**
 * Payload type flags.
 */
typedef enum NvDsPayloadType {
  NVDS_PAYLOAD_DEEPSTREAM,
  /** Reserved for future use. Use value greater than this for custom payloads. */
  NVDS_PAYLOAD_RESERVED = 0x100,
  /** To support custom payload. User need to implement nvds_msg2p_* interface */
  NVDS_PAYLOAD_CUSTOM = 0x101,
  NVDS_PAYLOAD_FORCE32 = 0x7FFFFFFF
} NvDsPayloadType;
/**
 * Holds rectangle parameters.
 */
typedef struct NvDsRect {
  gint top;
  gint left;
  gint width;
  gint height;
} NvDsRect;

/**
 * Holds Geo-location parameters.
 */
typedef struct NvDsGeoLocation {
  gdouble lat;
  gdouble lon;
  gdouble alt;
} NvDsGeoLocation;

/**
 * Hold coordinate parameters.
 */
typedef struct NvDsCoordinate {
  gdouble x;
  gdouble y;
  gdouble z;
} NvDsCoordinate;

/**
 * Holds object signature.
 */
typedef struct NvDsObjectSignature {
  /** array of signature values. */
  gdouble *signature;
  /** size of array */
  guint size;
} NvDsObjectSignature;

/**
 * Holds vehicle object parameters.
 */
typedef struct NvDsVehicleObject {
  gchar *type;
  gchar *make;
  gchar *model;
  gchar *color;
  gchar *region;
  gchar *license;
} NvDsVehicleObject;

/**
 * Holds person object parameters.
 */
typedef struct NvDsPersonObject {
  gchar *gender;
  gchar *hair;
  gchar *cap;
  gchar *apparel;
  guint age;
} NvDsPersonObject;

/**
 * Holds face parameters.
 */
typedef struct NvDsFaceObject {
  gchar *gender;
  gchar *hair;
  gchar *cap;
  gchar *glasses;
  gchar *facialhair;
  gchar *name;
  gchar *eyecolor;
  guint age;
} NvDsFaceObject;

/**
 * Holds event message meta data.
 *
 * Various types of objects (e.g. Vehicle, Person, Face etc.) can be
 * attached by allocating that object and setting @a extMsg pointer.
 *
 * Similarly custom object can also be allocated and set to @a extMsg
 * and should be handled by meta data parsing module accordingly.
 */
typedef struct NvDsEventMsgMeta {
  /** type of event */
  NvDsEventType type;
  /** type of object */
  NvDsObjectType objType;
  /** bounding box of object */
  NvDsRect bbox;
  /** Geo-location of object */
  NvDsGeoLocation location;
  /** coordinate of object */
  NvDsCoordinate coordinate;
  /** signature of object */
  NvDsObjectSignature objSignature;
  /** class id of object */
  gint objClassId;
  /** id of sensor that generated the event */
  gint sensorId;
  /** id of analytics module that generated the event */
  gint moduleId;
  /** id of place related to the object */
  gint placeId;
  /** id of component that generated this event */
  gint componentId;
  /** confidence of inference */
  gdouble confidence;
  /** tracking id of object */
  gint trackingId;
  /** time stamp of generated event */
  gchar *ts;
  /** id of detected / inferred object */
  gchar *objectId;
  /** other attributes associated with the object */
  gchar *otherAttrs;
  /** name of video file */
  gchar *videoPath;
  /**
   * To extend the event message meta data.
   * This can be used for custom values that can't be accommodated
   * in the existing fields OR if object(vehicle, person, face etc.) specific
   * values needs to be attached.
   */
  gpointer extMsg;
  /** size of custom object */
  guint extMsgSize;
} NvDsEventMsgMeta;
/**
 * Holds event information.
 */
typedef struct _NvDsEvent {
  /** type of event */
  NvDsEventType eventType;
  /** pointer of event meta data. */
  NvDsEventMsgMeta *metadata;
} NvDsEvent;

/**
 * Holds payload meta data.
 */
typedef struct NvDsPayload {
  /** pointer to payload */
  gpointer payload;
  /** size of payload */
  guint payloadSize;
  /** id of component who attached the payload (Optional) */
  guint componentId;
} NvDsPayload;

/** Defines DeepStream meta data types. */
typedef enum
{
    NVDS_META_INVALID=-1,
    /** Indicates that the meta data contains objects information (NvDsFrameMeta) */
    NVDS_META_FRAME_INFO = 0x01,
    /** Indicates that the meta data contains lines information for the given stream (NvDsLine_Params) */
    NVDS_META_LINE_INFO = 0x02,
    /** Payload for backend server as meta data */
    NVDS_META_PAYLOAD,
    /** event messages as meta data */
    NVDS_META_EVENT_MSG,
    NVDS_META_RESERVED = 0x100,
    /** Start adding custom meta types from here */
    NVDS_META_CUSTOM = 0x101,
    NVDS_META_FORCE32 = 0x7FFFFFFF
} NvDsMetaType;

/** Defines DeepStream meta surface types. */
typedef enum
{
    NVDS_META_SURFACE_NONE=0,
    /** Indicates that the meta data contains surface type */
    NVDS_META_SURFACE_FISH_PUSHBROOM=1,
    NVDS_META_SURFACE_FISH_VERTCYL=2,
} NvDsSurfaceType;

/**
 * Holds information about one secondary label attribute
 */
typedef struct _NvDsAttr {
  /** Attribute id */
  gshort attr_id;
  /** Attribute value */
  gshort attr_val;
  /** Attribute probability. This will have float value between 0 to 1 */
  gfloat attr_prob;
} NvDsAttr;

/** Holds data that secondary classifiers / custom elements update with
 *  secondary label information, such as car type, car color, etc.
 *  The structure may contain a string label. It may also contain a set of
 *  N(num_attrs) pairs of `<attr_id,attr_val>`.
 *
 *  For single label classifiers, `attr_id` will always be 0, and N=1.
 *  For multi-label classifiers, `attr_id` will be the index of the attribute
 *  type (e.g. 0 for Car type, 1 for Car make, ...).
 *  In both cases, `attr_val` will be the value of the attribute
 *  (e.g. 0 for Sedan, 1 for Coupe, ...)
 */
typedef struct _NvDsAttrInfo {
  /** Boolean indicating whether @a attr_label is valid. */
  gboolean is_attr_label;
  /** String label */
  gchar attr_label[64];
  /** Number of valid elements in the @a attrs array. */
  gint num_attrs;
  /** An array of attribute id and value, only @a num_attrs elements are valid. */
  NvDsAttr attrs[64];
} NvDsAttrInfo;

/** Holds extended parameters that describe meta data for the object. */
typedef struct _NvDsObjectParamsEx {
  gint param1;
  gint param2;
  gint param3;
  gint param4;
} NvDsObjectParamsEx;

/**
 * Holds the color parameters of the box or text to be overlayed.
 */
typedef struct _NvOSD_ColorParams {
  double red;                 /**< Holds red component of color.
                                   Value must be in the range 0-1. */

  double green;               /**< Holds green component of color.
                                   Value must be in the range 0-1.*/

  double blue;                /**< Holds blue component of color.
                                   Value must be in the range 0-1.*/

  double alpha;               /**< Holds alpha component of color.
                                   Value must be in the range 0-1.*/
} NvOSD_ColorParams;

/**
 * Holds the font parameters of the text to be overlayed.
 */
typedef struct _NvOSD_FontParams {
  const char * font_name;         /**< Holds pointer to the string containing
                                      font name. */

  unsigned int font_size;         /**< Holds size of the font. */

  NvOSD_ColorParams font_color;   /**< Holds font color. */
} NvOSD_FontParams;


/**
 * Holds the text parameters of the text to be overlayed.
 */

typedef struct _NvOSD_TextParams {
  char * display_text; /**< Holds the text to be overlayed. */

  unsigned int x_offset; /**< Holds horizontal offset w.r.t top left pixel of
                             the frame. */
  unsigned int y_offset; /**< Holds vertical offset w.r.t top left pixel of
                             the frame. */

  NvOSD_FontParams font_params;/**< font_params. */

  int set_bg_clr; /**< Boolean to indicate text has background color. */

  NvOSD_ColorParams text_bg_clr; /**< Background color for text. */

} NvOSD_TextParams;

/**
 * Holds the box parameters of the box to be overlayed.
 */
typedef struct _NvOSD_RectParams {
  unsigned int left;   /**< Holds left coordinate of the box in pixels. */

  unsigned int top;    /**< Holds top coordinate of the box in pixels. */

  unsigned int width;  /**< Holds width of the box in pixels. */

  unsigned int height; /**< Holds height of the box in pixels. */

  unsigned int border_width; /**< Holds border_width of the box in pixels. */

  NvOSD_ColorParams border_color; /**< Holds color params of the border
                                      of the box. */

  unsigned int has_bg_color;  /**< Holds boolean value indicating whether box
                                    has background color. */

  unsigned int reserved; /**< Reserved field for future usage.
                             For internal purpose only */

  NvOSD_ColorParams bg_color; /**< Holds background color of the box. */
} NvOSD_RectParams;

/**
 * Holds the box parameters of the line to be overlayed.
 */
typedef struct _NvOSD_LineParams {
  unsigned int x1;   /**< Holds left coordinate of the box in pixels. */

  unsigned int y1;    /**< Holds top coordinate of the box in pixels. */

  unsigned int x2;  /**< Holds width of the box in pixels. */

  unsigned int y2; /**< Holds height of the box in pixels. */

  unsigned int line_width; /**< Holds border_width of the box in pixels. */

  NvOSD_ColorParams line_color; /**< Holds color params of the border
                                        of the box. */
} NvOSD_LineParams;

/**
 * List modes used to overlay boxes and text
 */
typedef enum {
    NV_OSD_MODE_CPU, /**< Selects CPU for OSD processing.
                Works with RGBA data only */
    NV_OSD_MODE_GPU, /**< Selects GPU for OSD processing.
                Works with RGBA data only */
} NvOSD_Mode;

/** Holds parameters that describe meta data for one object. */
typedef struct _NvDsObjectParams {
  /** Structure containing the positional parameters of the object in the frame.
   *  Can also be used to overlay borders / semi-transparent boxes on top of objects
   *  Refer NvOSD_RectParams from nvosd.h
   */
  NvOSD_RectParams rect_params;
  /** Text describing the object can be overlayed using this structure.
   *  @see NvOSD_TextParams from nvosd.h. */
  NvOSD_TextParams text_params;
  /** Index of the object class infered by the primary detector/classifier */
  gint class_id;
  /** Unique ID for tracking the object. This -1 indicates the object has not been
   * tracked. Custom elements adding new NvDsObjectParams should set this to
   * -1. */
  gint tracking_id;
  /** Secondary classifiers / custom elements update this structure with
   *  secondary classification labels. Each element will only update the
   *  attr_info structure at index specified by the element's unique id.
   */
  NvDsAttrInfo attr_info[NVDS_MAX_ATTRIBUTES];
  /** Boolean indicating whether attr_info contains new information. */
  gboolean has_new_info;
  /** Boolean indicating whether secondary classifiers should run inference on the object again. Used internally by components. */
  gboolean force_reinference;
  /** Used internally by components. */
  gint parent_class_id;
  /** Used internally by components. */
  struct _NvDsObjectParams *parent_roi;
  /** Used internally by components */
  NvOSD_LineParams line_params[4];
  /** Used internally by components */
  gint lines_present;
  /** Used internally by components */
  gint obj_status;
  /** Provision to add custom object metadata info */
  NvDsObjectParamsEx obj_params_ex;
} NvDsObjectParams;

/** Holds data that describes metadata objects in the current frame.
    `meta_type` member of @ref NvDsMeta must be set to `NVDS_META_FRAME_INFO`. */
typedef struct _NvDsFrameMeta {
  /** Array of NvDsObjectParams structure describing each object. */
  NvDsObjectParams *obj_params;
  /** Number of rectangles/objects i.e. length of @ref NvDsObjectParams */
  guint num_rects;
  /** Number of valid strings in @ref NvDsObjectParams. */
  guint num_strings;
  /** Index of the frame in the batched buffer to which this meta belongs to. */
  guint batch_id;
  /** NvOSD mode to be used. @see NvOSD_Mode in `nvosd.h`. */
  NvOSD_Mode nvosd_mode;
  /** 1 = Primary GIE, 2 = Secondary GIE, 3 = Custom Elements */
  gint gie_type;
  /** Batch size of the primary detector. */
  gint gie_batch_size;
  /** Unique ID of the primary detector that attached this metadata. */
  gint gie_unique_id;
  /** Frame number. */
  gint frame_num;
  /** Index of the stream this params structure belongs to. */
  guint stream_id;
  /** Boolean indicating if these params are no longer valid. */
  gint is_invalid;
  /** Indicates Surface Type i.e. Spot or Aisle */
  NvDsSurfaceType surface_type;
  /** Indicates Surface Index for SurfaceType Spot or Aisle */
  gint camera_id;
  /** Indicates Surface Index for SurfaceType Spot or Aisle */
  gint surface_index;
} NvDsFrameMeta;

/** Holds line meta data. */
typedef struct _NvDsLineMeta {
  /** Index of the frame in the batched buffer to which this meta belongs to. */
  guint batch_id;
  /** number of lines to be drawn i.e. valid length of @ref NvDsLineMeta . */
  guint num_lines;
  /** Array of NvDsLineMeta structure describing each line. */
  NvOSD_LineParams *line_params;
} NvDsLineMeta;

/** Holds DeepSteam meta data. */
 typedef struct _NvDsMeta {
  GstMeta       meta;
  /** Must be cast to another structure based on @a meta_type. */
  gpointer meta_data;
  gpointer user_data;
  /** Type of metadata, from the @ref meta_type enum. */
  gint meta_type;
  /** Function called with meta_data pointer as argument when the meta is going to be destroyed.
   * Can be used to clear/free meta_data.
   * Refer to https://developer.gnome.org/glib/unstable/glib-Datasets.html#GDestroyNotify */
  /* GDestroyNotify destroy; */
  /**
   * It is called when meta_data needs to copied / transformed
   * from one buffer to other. meta_data and user_data are passed as arguments.
   */
  /* NvDsMetaCopyFunc copyfunc; */
  /**
   * It is called when meta_data is going to be destroyed.
   * Both destroy or freefunc must not be set. User freefunc only if
   * GDestroyNotify is not sufficient to release the resources.
   * meta_data and user_data are passed as arguments.
   */
  /* NvDsMetaFreeFunc freefunc; */
  ...;
} NvDsMeta;

/**
 * Holds information related to the original buffers contained in a batched
 * buffer.
 */
typedef struct
{
  /** Parent GstMeta structure. */
  GstMeta meta;
  /** Number of actual filled frames in a batch. This number may be less than
   * the batch size of the buffer. */
  guint num_filled;

  /** Array of indexes of stream to which the frames in the batch belong to. */
  guint *stream_id;
  /** Array of frame numbers of the frames in the batch. The frame numbers are
   * the numbers of the frame in the input stream. */
  gulong *stream_frame_num;
  /** Array of original input widths of the frames in the batch. This might be
   * different than the width of the batched frame since the Stream Muxer might
   * scale the frame during batching. */
  guint *original_width;
  /** Array of original input heights of the frames in the batch. This might be
   * different than the width of the batched frame since the Stream Muxer might
   * scale the frame during batching. */
  guint *original_height;
  /** Array of original presentation timestamps of the frames in the batch.
   * Stream Muxer will attach its own timestamp to the batched GstBuffer. */
  GstClockTime *buf_pts;

  /** Array of Camera IDs indicating the camera_id which maps to CSV file */
  guint *camera_id;
  /** Total number of dewarped surfaces per source frame */
  guint num_surfaces_per_frame;
  /** Total batch-size */
  guint batch_size;
  /** Array of Surface Types Spot / Aisle / None */
  NvDsSurfaceType *surface_type;
  /** Array of surface_index indicating the surface index which maps to CSV file */
  guint *surface_index;

  /** Used internally by components. */
  gchar **input_pkt_pts;
  /** Used internally by components. */
  gboolean *is_valid;
} GstNvStreamMeta;

