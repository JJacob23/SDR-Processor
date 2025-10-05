import argparse, time, numpy as np
from datetime import datetime
from gnuradio import gr, blocks, analog, audio, filter
import osmosdr

def measure_power(src, dwell=0.05):
    '''
    Measure power of a tuning.
    Used for automatically doing fine adjustments for best signal
    '''
    tb = gr.top_block()
    mag2 = blocks.complex_to_mag_squared(1)
    avg = blocks.moving_average_ff(1024, 1.0/1024, 4000)
    probe = blocks.probe_signal_f()
    tb.connect(src, mag2, avg, probe)
    tb.start()
    time.sleep(dwell)
    p = probe.level()
    tb.stop(); tb.wait()
    return p

def fine_scan(src, base_freq, span=10e3, step=2e3, dwell=0.05):
    """
    Sweep ±span (Hz) around base_freq in 'step' increments.
    Return the offset (Hz) that gives max power.
    """
    offsets = np.arange(-span, span+step, step)
    best_offset, best_pwr = 0.0, -1e12
    for off in offsets:
        src.set_center_freq(base_freq + off)
        pwr = measure_power(src, dwell=dwell)
        if pwr > best_pwr:
            best_pwr, best_offset = pwr, off
    return best_offset


class FMRx(gr.top_block):
    '''
    returns a new Rx with configured gnuradio chain
    '''
    def __init__(self, freq, gain, ppm=0.0, outfile=None, play_audio=True, auto_fine=False):
        gr.top_block.__init__(self)

        #Correct for ppm
        freq_hw = freq / (1.0 - ppm/1e6)

        self.src = osmosdr.source(args="numchan=1")
        self.src.set_sample_rate(240e3)
        try:
            self.src.set_gain_mode(True)
        except Exception:
            print(f"Unable to set AGC, using {gain} gain")
            self.src.set_gain(gain)

        if auto_fine:
            fine_off = fine_scan(self.src, freq_hw, span=10e3, step=2e3)
            freq_hw += fine_off
            print(f"Fine-tuned by {fine_off:+.0f} Hz → {freq_hw/1e6:.6f} MHz")

        self.src.set_center_freq(freq_hw)

        #Fight clicking with high pass filter
        #TODO: Consider sampling off frequency and then resampling as an alternative, thats how RTL_FM does it.
        self.dcblock = filter.dc_blocker_cc(1024, True)
        #Convert IQ to normalized floats
        self.wbfm = analog.wfm_rcv(quad_rate=240e3, audio_decimation=5)
        #Fight hiss by pushing down high frequencies
        self.deemph = analog.fm_deemph(fs=48000, tau=75e-6)

        #Save audio to .wav file
        if outfile:
            self.wav_sink = blocks.wavfile_sink(
                outfile, 1, 48000,
                blocks.wavfile_format_t.FORMAT_WAV,
                blocks.wavfile_subformat_t.FORMAT_PCM_16
            )
            self.connect(self.deemph, self.wav_sink)

        #Play audio through speakers
        if play_audio:
            self.audio = audio.sink(48000, "", True)
            self.connect(self.deemph, self.audio)

        self.connect(self.src, self.dcblock, self.wbfm, self.deemph)
