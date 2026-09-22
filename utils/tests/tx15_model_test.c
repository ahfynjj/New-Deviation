/* Integration tests linked to the actual Windows TX15 emulator objects. */
#include <assert.h>
#include "common.h"
#include "config/model.h"
#include "config/tx.h"
#include "mixer_standard.h"
#include "target/drivers/mcu/emu/fltk.h"

static void write_file(const char *path, const char *text)
{
    FILE *fp = fopen(path, "w");
    assert(fp);
    assert(fputs(text, fp) >= 0);
    assert(fclose(fp) == 0);
}

int __wrap_main(void)
{
    assert(FS_Init());
    CONFIG_LoadTx();
    write_file("models/model2.ini", "[mixer]\nsrc=FMODE0\ndest=Ch1\n");
    assert(!CONFIG_ReadModel(2));
    assert(strcmp(Model.name, "Load failed") == 0);
    assert(!CONFIG_WriteModel(2));
    assert(CONFIG_ReadModel(1));
    struct Model original = Model;
    write_file("models/model2.ini", "name=Legacy\n[mixer]\nsrc=AIL\ndest=Ch1\nswitch=FMODE1\n");
    assert(!CONFIG_ReadModel(2));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    assert(CONFIG_GetCurrentModel() == 1);
    assert(!CONFIG_WriteModel(2));
    assert(!CONFIG_SaveModelIfNeeded());
    assert(CONFIG_ReadModel(1));

    /* Canonical source names, inversions and all switch positions round-trip. */
    for (int src = 1; src <= NUM_TX_INPUTS; src++) {
        Model.mixers[0].src = src | 0x80;
        Model.mixers[0].sw = src;
        Model.mixers[0].dest = 0;
        assert(CONFIG_WriteModel(3));
        assert(CONFIG_ReadModel(3));
        assert(Model.mixers[0].src == (src | 0x80));
        assert(Model.mixers[0].sw == src);
    }
    original = Model;
    write_file("template/bad.ini", "[mixer]\nsrc=S1\ndest=Ch1\nswitch=GEAR1\n");
    assert(!CONFIG_ReadTemplate("bad.ini"));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    write_file("models/model4.ini", "[trim1]\nsrc=AIL\npos=TRIM_L+\n");
    assert(!CONFIG_ReadModel(4));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    assert(CONFIG_ReadModel(1));
    assert(!CONFIG_ReadModel(250)); /* missing file must not become a saved blank model */
    assert(!CONFIG_WriteModel(250));
    assert(CONFIG_ReadModel(1));
    assert(CONFIG_ReadTemplate("heli_std.ini"));
    assert(Model.mixer_mode == MIXER_STANDARD);
    int compatibility_failures = 0;
    const char *templates[] = {"6chplane.ini", "6ch_heli.ini", "heli_std.ini"};
    for (unsigned i = 0; i < sizeof(templates) / sizeof(templates[0]); i++) {
        int loaded = CONFIG_ReadTemplate(templates[i]);
        printf("Template %s: %s\n", templates[i], loaded ? "PASS" : "FAIL");
        compatibility_failures += !loaded;
    }
    STDMIXER_InitSwitches();
    for (unsigned i = 0; i < NUM_MIXERS; i++) {
        if (!Model.mixers[i].src) continue;
        if (Model.mixers[i].dest == mapped_std_channels.aile)
            assert(Model.mixers[i].src == INP_AILERON);
        if (Model.mixers[i].dest == mapped_std_channels.elev)
            assert(Model.mixers[i].src == INP_ELEVATOR);
    }
    int rates_ok = INPUT_GetFirstSwitch(mapped_std_channels.switches[SWITCHFUNC_DREXP_AIL]) == INP_SWC0
                && INPUT_GetFirstSwitch(mapped_std_channels.switches[SWITCHFUNC_DREXP_ELE]) == INP_SWD0;
    printf("Standard rate defaults: %s\n", rates_ok ? "PASS" : "FAIL");
    compatibility_failures += !rates_ok;
    original = Model;
    assert(STDMIXER_ValidateTraditionModel());
    Model.mixer_mode = MIXER_ADVANCED;
    for (unsigned i = 0; i < NUM_MIXERS; i++) {
        if (Model.mixers[i].src && Model.mixers[i].sw) {
            Model.mixers[i].sw = INP_SW65;
            break;
        }
    }
    int invalid_accepted = STDMIXER_ValidateTraditionModel();
    printf("Reject six-position Standard conversion: %s\n", invalid_accepted ? "FAIL" : "PASS");
    compatibility_failures += invalid_accepted;
    Model = original;
    fflush(stdout);
    assert(compatibility_failures == 0);
    for (int src = 0; src <= NUM_SOURCES; src++) {
        for (int dir = -1; dir <= 1; dir++) {
            int sw = STDMIXER_SelectSwitch(src, dir);
            assert(INPUT_NumSwitchPos(sw) >= 2 && INPUT_NumSwitchPos(sw) <= 3);
        }
    }
    original = Model;
    mapped_std_channels.switches[SWITCHFUNC_FLYMODE] = INP_SW60;
    STDMIXER_SaveSwitches();
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    STDMIXER_Preset();
    original = Model;
    write_file("template/bad.ini", "[trim1]\nsrc=AIL\nswitch=FMODE\n");
    assert(!CONFIG_ReadTemplate("bad.ini"));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    write_file("layout/bad.ini", "[gui-480x320]\nToggle=10,10,1,2,3,FMODE\n");
    assert(!CONFIG_ReadLayout("layout/bad.ini"));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    assert(CONFIG_WriteModel(5));
    assert(CONFIG_ReadModel(5));
    assert(Model.mixer_mode == MIXER_STANDARD);
    original = Model;
    write_file("template/bad.ini", "mixermode=Standard\n[mixer]\nsrc=THR\ndest=Ch3\nswitch=6POS5\n");
    assert(!CONFIG_ReadTemplate("bad.ini"));
    assert(memcmp(&Model, &original, sizeof(Model)) == 0);
    assert(CONFIG_ReadModel(1));
    memset(Model.mixers, 0, sizeof(Model.mixers));
    Model.templates[0] = MIXERTEMPLATE_COMPLEX;
    for (int n = 0; n < 6; n++) {
        Model.mixers[n].src = INP_S1;
        Model.mixers[n].sw = INP_SW60 + n;
        Model.mixers[n].dest = 0;
        Model.mixers[n].scalar = 10 * (n + 1);
    }
    assert(CONFIG_WriteModel(6));
    assert(CONFIG_ReadModel(6));
    MIXER_Init();
    gui.aux2 = 10;
    for (int n = 0; n < 6; n++) {
        EMU_HandleTargetKey('1' + n, 1);
        MIXER_CalcChannels();
        assert(Channels[0] == 1000 * (n + 1));
    }
    puts("PASS TX15 native model integration");
    return 0;
}
