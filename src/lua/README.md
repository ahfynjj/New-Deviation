# Native Deviation ELRS Lua tools

Embeds the unchanged official ExpressLRS `elrs.lua` r18 at commit
`670c8099a91da6c8f5baa44edbdecfacb0e0c6da`. `sources.json` records script SHA256
and Lua 5.2.4 archive SHA256. The resource generator checks the script hash.

- https://github.com/ExpressLRS/Lua/blob/670c8099a91da6c8f5baa44edbdecfacb0e0c6da/elrs.lua
- https://www.lua.org/ftp/lua-5.2.4.tar.gz

Vendor Lua sources are unchanged; the MIT notice is in `vendor/lua-5.2.4/src/lua.h`.
The official script retains its GPLv2 header; new adapters follow Deviation's
GPL-3.0-or-later license.

## Build and scope

`TX15_ELRS_LUA=1` enables a temporary, read-only internal-module tool session.
It cannot be combined with `TX15_ELRS_DISCOVERY` or `TX15_ELRS_PARAMETERS`.
Ordinary builds leave RF off. No Flash/TF installation is added.

The 480x320 color API uses native Deviation fonts/framebuffer. Virtual events
map to wheel/ENTER/EXIT; holding EXIT leaves the tool. Legacy arrow bytes become
ASCII ^/v. Text is validated as UTF-8 and padded for native decoder lookahead.
`getVersion()` identifies Deviation. `model.getModule()` reads the actual CRSF
session (internal=0, external=1). The board selects internal for this bench;
external hardware/model UI are pending. Source tools return `init`/`run`.
TF script loading is later; the current script is embedded as a resource.

The first bench powers the module for up to 120 seconds, delivers validated
extended replies to Lua, and sends ping 0x28, parameter read 0x2C and statistics queries.
The exact ELRS link-statistics query (0x2D, EE EA 00 00) is allowed separately
from parameter writes. Default Lua builds remain read-only for parameters;
there is no RC output. Errors/exit close the module and return to the native GUI.

`TX15_ELRS_WRITE=1`, together with `TX15_ELRS_LUA=1`, opts into visible
TEXT_SELECTION settings only. Their complete, ordered, bounded metadata must
have been read in this session; values must be in range and choose a nonempty
option. Command, info, folder, string, float and integer writes remain blocked.
Both the interpreter API and UART adapter enforce the policy. Forbidden queued
frames are removed, while busy or settling retains legitimate frames.

A UART-accepted save starts a 200ms settling interval and a 3s readback deadline.
The official Lua reread waits in the queue until settling completes, including
when UART acceptance was delayed. A complete reread with matching schema/index
is reported as verified; mismatch, timeout and cancellation are distinct.
One save can wait for verification at a time. No automatic retry or rollback
issues another save. The user restores the original setting explicitly.

Readback relies on the local module replying within the settling/response
windows. CRSF has no request nonce, so field/chunk/schema matching cannot
exclude arbitrarily delayed duplicate replies. This checks observed runtime
values; cold-start persistence and real-time RC continuity require later bench
acceptance. The official script is unchanged.

## Bounds

Lua owns a 160KiB AXI RAM arena, separate from a 16KiB bounded newlib heap for
numeric formatting. VM count hooks allow 120000 instructions per init/run,
with separate 1000ms initialization and 250ms read-only tool run checks; drawing is limited to 256 calls, text to 256 bytes,
source to 64KiB, coordinates to ±1024. Frame queues use existing CRSF bounds.
Module session generation/slot changes abort the tool.

Initialization includes source parsing and is reported separately from the
worst run time. Elapsed time is checked again after protected C/Lua calls,
including a final C drawing call with no subsequent VM instructions.

Last-call counters measure allocator, explicit GC, native drawing and hook
service time to diagnose repeatable board stalls. GC includes its allocator
cost; drawing includes text dimensions and any platform polling it performs.
These overlapping measurements must not be added as disjoint totals.

The arena searches size-class free lists and coalesces neighboring free blocks;
it does not scan live Lua objects for each new allocation. Metadata uses fixed
32-bit offsets so host and board exercise the same 16-byte block layout.

Base/table/string/math/bit32 are available. OS/io/debug/package/coroutine,
file/dynamic loading and printing are absent. `pcall`/`xpcall` rethrow budget
exhaustion; table finalizers are denied because Lua 5.2 runs them with hooks
disabled. C library/GC operations are not preempted by the VM hook; worst-case
timing and future RC scheduling require board measurement. This is a limited
source-script API compatibility layer, not full EdgeTX API support.

## Verification

`python -m unittest discover -s utils/hardware/tests` runs actual Lua C with
the official script, parameter/folder API calls, OOM/errors, nested protected
call budgets, finalizer denial, text validation, route changes, UART busy and
read-only boundaries. This is API testing, not a radio simulator. Optional
`TX15_LUA_CAPTURE` points to the private 2026-10-02 bench JSON to replay all
33 captured fields without publishing them. Board results are in `docs/tx15/`.
