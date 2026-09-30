/* New Deviation RAM application resources; GPL-3.0-or-later.
 * No media-device access; writes fail explicitly. Models edited by the GUI
 * are volatile until the later storage milestone.
 */
#include "common.h"
#include "romfs.h"
struct handle { const struct tx15_resource *resource; size_t pos; };
static struct handle handles[8];
static struct handle *get(FILE *stream) {
    for(unsigned i=0;i<8;i++) if(stream==(FILE *)&handles[i] && handles[i].resource) return &handles[i];
    return NULL;
}
FILE *devo_fopen2(void *unused,const char *path,const char *mode) {
    (void)unused;
    if(!path || !mode || (strcmp(mode,"r") && strcmp(mode,"rb"))) return NULL;
    for(size_t n=0;n<tx15_resource_count;n++) if(!strcmp(path,tx15_resources[n].path))
        for(unsigned i=0;i<8;i++) if(!handles[i].resource) {
            handles[i].resource=&tx15_resources[n]; handles[i].pos=0; return (FILE *)&handles[i];
        }
    return NULL;
}
int devo_fclose(FILE *stream) {
    struct handle *h=get(stream); if(!h) return -1; h->resource=NULL; h->pos=0; return 0;
}
size_t devo_fread(void *dst,size_t size,size_t count,FILE *stream) {
    struct handle *h=get(stream);
    if(!h || !dst || !size || count>SIZE_MAX/size) return 0;
    size_t want=size*count, available=h->resource->size-h->pos;
    size_t n=want<available?want:available;
    memcpy(dst,h->resource->data+h->pos,n); h->pos+=n; return n/size;
}
int devo_fseek(FILE *stream,long offset,int whence) {
    struct handle *h=get(stream); if(!h) return -1;
    int64_t base;
    if(whence==SEEK_SET) base=0;
    else if(whence==SEEK_CUR) base=h->pos;
    else if(whence==SEEK_END) base=h->resource->size;
    else return -1;
    int64_t p=base+offset;
    if(p<0 || (uint64_t)p>h->resource->size) return -1;
    h->pos=(size_t)p; return 0;
}
long devo_ftell(FILE *stream) { struct handle *h=get(stream); return h?(long)h->pos:-1; }
char *devo_fgets(char *dst,int length,FILE *stream) {
    if(!dst || length<2) return NULL;
    int n=0; char ch;
    while(n<length-1 && devo_fread(&ch,1,1,stream)==1) { dst[n++]=ch; if(ch=='\n') break; }
    dst[n]=0; return n?dst:NULL;
}
void devo_setbuf(FILE *stream,char *buf) { (void)stream; (void)buf; }
void devo_finit(FSHANDLE *h,const char *drive) { (void)h; (void)drive; }
size_t devo_fwrite(void *p,size_t s,size_t n,FILE *f) { (void)p;(void)s;(void)n;(void)f;return 0; }
int devo_fputc(int c,FILE *f) { (void)c;(void)f;return -1; }
void fempty(FILE *f) { (void)f; }
