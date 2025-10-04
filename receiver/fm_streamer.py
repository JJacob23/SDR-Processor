import os, time, signal
from gnuradio import gr,blocks
from fm_receiver import FMRx 

class StreamRecorder:
    '''
    Saves 10 seconds of data as a wav file for the classifier to pick up.
    This stutters on restart and is just a proof of concept untill queuing can be implemented
    '''
    def __init__(self, freq, gain, outdir, chunk_len, play_audio):
        self.freq = freq
        self.gain = gain
        self.outdir = outdir
        self.chunk_len = chunk_len
        self.running = True
        self.play_audio = play_audio
        os.makedirs(outdir, exist_ok=True)

        self.rx = FMRx(freq=freq, gain=gain, outfile=None, play_audio=play_audio)
        print(f"Ready to record from {freq/1e6:.2f} MHz")

    def record_chunk(self):
        """
        Disconnect old sinks, attach new WAV sink, run for 10 seconds, stop.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(self.outdir, f"{timestamp}.wav")

        # Create and wire a new sink
        wav_sink = blocks.wavfile_sink(out_path, 1, 48000,
                                          blocks.wavfile_format_t.FORMAT_WAV,
                                          blocks.wavfile_subformat_t.FORMAT_PCM_16)
        if hasattr(self.rx, "wav_sink"):
            self.rx.disconnect(self.rx.deemph, self.wav_sink)
        self.rx.connect(self.rx.deemph, wav_sink)

        self.rx.start()
        time.sleep(self.chunk_len)
        self.rx.stop()
        self.rx.wait()

        print(f"Saved {out_path}")

    def stop(self, *_):
        print("\nStopping recorder...")
        self.running = False
        self.rx.stop()
        self.rx.wait()

    def run(self):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        while self.running:
            self.record_chunk()

def main():
    rec = StreamRecorder(freq=100.304e6, gain=25, outdir="data/live", chunk_len=10, play_audio=True, )
    rec.run()

if __name__ == "__main__":
    main()

