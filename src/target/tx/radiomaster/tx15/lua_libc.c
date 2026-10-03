/* Newlib capability limits for the opt-in Lua tool; GPL-3.0-or-later.
 * Lua itself uses nd_arena. Newlib numeric formatting has a separate bounded
 * heap; file/console/OS capabilities fail, rather than touching media or USB.
 */
#ifdef TX15_ELRS_LUA
#include <stddef.h>
#include <stdint.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/time.h>
static union { double align; unsigned char bytes[16384]; } libc_heap;
static size_t libc_break;
void *_sbrk(ptrdiff_t increment)
{
    if(increment<0 || (size_t)increment>sizeof(libc_heap.bytes)-libc_break) {errno=ENOMEM;return (void *)-1;}
    void *result=libc_heap.bytes+libc_break;libc_break+=(size_t)increment;return result;
}
int _open(const char *path,int flags,...) { (void)path;(void)flags;errno=ENOSYS;return -1; }
int _close(int fd) { (void)fd;errno=ENOSYS;return -1; }
int _read(int fd,void *data,size_t size) { (void)fd;(void)data;(void)size;errno=ENOSYS;return -1; }
int _write(int fd,const void *data,size_t size) { (void)fd;(void)data;(void)size;errno=ENOSYS;return -1; }
int _lseek(int fd,int offset,int whence) { (void)fd;(void)offset;(void)whence;errno=ENOSYS;return -1; }
int _fstat(int fd,struct stat *st) { (void)fd;(void)st;errno=ENOSYS;return -1; }
int _isatty(int fd) { (void)fd;return 0; }
int _gettimeofday(struct timeval *tv,void *tz) { (void)tv;(void)tz;errno=ENOSYS;return -1; }
int _getpid(void) { return 1; }
int _kill(int pid,int sig) { (void)pid;(void)sig;errno=ENOSYS;return -1; }
void App_Fault(void);
void _exit(int status) { (void)status;App_Fault();for(;;) {} }
#endif
