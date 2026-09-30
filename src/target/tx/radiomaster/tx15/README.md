# Native TX15 application integration (P2 in progress)

Build on the existing Windows toolchain with `python utils/build-tx15-app.py`
from the repository root. This builds original Deviation GUI, main/mixer pages,
model/mixer code and the native LCD/read-only resource adapters for Cortex-M7.
It is not an emulator and creates no flashable or loadable firmware yet.

`local/tx15-hardware/app/` contains the integration archive, relocatable object,
compile log and `unresolved.txt`. The latter is the explicit remaining runtime
interface inventory; an archive/relocatable link is not a successful application
link. The current app entry is not included in any existing bench-load profile.

Resources are regenerated from tracked files; 15normal/23bold are ASCII font
subsets for the first hardware page pass. File reads use the original Deviation
font/image decoders. Writes fail, so this build must not advertise model saving.
The fixed test model is not a user's existing model file.

Before board execution: finish runtime services/button translation, final link
and memory map; separate the already-proven RAM bootstrap from the larger
application/resources; verify owned write ranges and the original recovery path.
P0/P1 builds remain the hardware-verified targets until then.
