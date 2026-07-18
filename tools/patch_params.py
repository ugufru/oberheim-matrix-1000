"""Matrix-1000 patch parameter labels and the internal-buffer mapping.

The firmware's unpacked working buffer (tools/unpack_patch.py output) holds the
126 parameters numbered 8..133 in the canonical Matrix-6/1000 parameter model
(docs/patch-rom/parameter-map.md). The mapping is simply:

    internal_buffer[i]  ==  SysEx parameter (i + 8)

Parameters 0..7 are the (8-char) patch name, which the Matrix-1000 does NOT store
(it is a number-addressed rack with no name display), so the 80-byte record is
parameters only. Verified: across all 819 ROM records, every narrow bitfield
(2/3-bit params) lands in range under this mapping.
"""

NAME_OFFSET = 8  # internal_buffer[i] == parameter (i + NAME_OFFSET)

# Parameter number -> (label, signed?) for the parameters the M1000 stores (8..133).
PARAMS = {
    8: ("keyboard_mode", False),
    9: ("dco1_freq", False), 10: ("dco1_saw", False), 11: ("dco1_pw", False),
    12: ("dco1_freq_mod_sel", False), 13: ("dco1_wave_enable", False),
    14: ("dco2_freq", False), 15: ("dco2_saw", False), 16: ("dco2_pw", False),
    17: ("dco2_freq_mod_sel", False), 18: ("dco2_wave_enable", False),
    19: ("dco2_detune", True), 20: ("dco_mix", False),
    21: ("dco1_kbd_porta", False), 22: ("dco1_click", False),
    23: ("dco2_kbd_porta", False), 24: ("dco2_click", False), 25: ("dco_sync", False),
    26: ("vcf_freq", False), 27: ("vcf_reso", False), 28: ("vcf_freq_mod_sel", False),
    29: ("vcf_kbd_porta", False), 30: ("vcf_fm", False), 31: ("vca1_level", False),
    32: ("porta_rate", False), 33: ("porta_mode", False), 34: ("legato", False),
    35: ("lfo1_speed", False), 36: ("lfo1_trigger", False), 37: ("lfo1_lag", False),
    38: ("lfo1_wave", False), 39: ("lfo1_retrig", False), 40: ("lfo1_samp_src", False),
    41: ("lfo1_amp", False),
    42: ("lfo2_speed", False), 43: ("lfo2_trigger", False), 44: ("lfo2_lag", False),
    45: ("lfo2_wave", False), 46: ("lfo2_retrig", False), 47: ("lfo2_samp_src", False),
    48: ("lfo2_amp", False),
    49: ("env1_trigger", False), 50: ("env1_delay", False), 51: ("env1_attack", False),
    52: ("env1_decay", False), 53: ("env1_sustain", False), 54: ("env1_release", False),
    55: ("env1_amp", False), 56: ("env1_lfo_trig", False), 57: ("env1_mode", False),
    58: ("env2_trigger", False), 59: ("env2_delay", False), 60: ("env2_attack", False),
    61: ("env2_decay", False), 62: ("env2_sustain", False), 63: ("env2_release", False),
    64: ("env2_amp", False), 65: ("env2_lfo_trig", False), 66: ("env2_mode", False),
    67: ("env3_trigger", False), 68: ("env3_delay", False), 69: ("env3_attack", False),
    70: ("env3_decay", False), 71: ("env3_sustain", False), 72: ("env3_release", False),
    73: ("env3_amp", False), 74: ("env3_lfo_trig", False), 75: ("env3_mode", False),
    76: ("trk_source", False), 77: ("trk_pt1", False), 78: ("trk_pt2", False),
    79: ("trk_pt3", False), 80: ("trk_pt4", False), 81: ("trk_pt5", False),
    82: ("ramp1_rate", False), 83: ("ramp1_mode", False),
    84: ("ramp2_rate", False), 85: ("ramp2_mode", False),
    # 86..103 = dedicated (signed) mod amounts
    86: ("m_dco1f_by_lfo1", True), 87: ("m_dco1pw_by_lfo2", True),
    88: ("m_dco2f_by_lfo1", True), 89: ("m_dco2pw_by_lfo2", True),
    90: ("m_vcff_by_env1", True), 91: ("m_vcff_by_press", True),
    92: ("m_vca1_by_vel", True), 93: ("m_vca2_by_env2", True),
    94: ("m_env1amp_by_vel", True), 95: ("m_env2amp_by_vel", True),
    96: ("m_env3amp_by_vel", True), 97: ("m_lfo1amp_by_ramp1", True),
    98: ("m_lfo2amp_by_ramp2", True), 99: ("m_porta_by_vel", True),
    100: ("m_vcffm_by_env3", True), 101: ("m_vcffm_by_press", True),
    102: ("m_lfo1spd_by_press", True), 103: ("m_lfo2spd_by_kbd", True),
}
# 104..133 = 10 programmable matrix buses (source, amount(signed), destination)
for _n in range(10):
    b = 104 + 3 * _n
    PARAMS[b] = ("mod%d_source" % _n, False)
    PARAMS[b + 1] = ("mod%d_amount" % _n, True)
    PARAMS[b + 2] = ("mod%d_dest" % _n, False)


# Matrix modulation source codes (source field of a bus); 0 = unused.
SOURCES = {
    0: "unused", 1: "Env1", 2: "Env2", 3: "Env3", 4: "LFO1", 5: "LFO2",
    6: "Vibrato", 7: "Ramp1", 8: "Ramp2", 9: "Keyboard", 10: "Portamento",
    11: "TrackGen", 12: "KbdGate", 13: "Velocity", 14: "RelVelocity",
    15: "Pressure", 16: "Pedal1", 17: "Pedal2", 18: "Lever1", 19: "Lever2",
    20: "Lever3",
}

# Matrix modulation destination codes (destination field of a bus); 0 = unused.
DESTS = {
    0: "unused", 1: "DCO1 Freq", 2: "DCO1 PW", 3: "DCO1 Wave", 4: "DCO2 Freq",
    5: "DCO2 PW", 6: "DCO2 Wave", 7: "Mix", 8: "VCF FM", 9: "VCF Freq",
    10: "VCF Reso", 11: "VCA1", 12: "VCA2", 13: "Env1 Delay", 14: "Env1 Attack",
    15: "Env1 Decay", 16: "Env1 Release", 17: "Env1 Amp", 18: "Env2 Delay",
    19: "Env2 Attack", 20: "Env2 Decay", 21: "Env2 Release", 22: "Env2 Amp",
    23: "Env3 Delay", 24: "Env3 Attack", 25: "Env3 Decay", 26: "Env3 Release",
    27: "Env3 Amp", 28: "LFO1 Speed", 29: "LFO1 Amp", 30: "LFO2 Speed",
    31: "LFO2 Amp", 32: "Porta Time",
}


def labelled(buf):
    """Map an unpacked buffer (params 8..133) to {param_name: value}."""
    out = {}
    for pnum, (name, signed) in PARAMS.items():
        idx = pnum - NAME_OFFSET
        if 0 <= idx < len(buf):
            v = buf[idx]
            if signed and v > 63:
                v -= 128
            out[name] = v
    return out
