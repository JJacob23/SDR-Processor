from fm_receiver import FMRx
import argparse

def main():
    '''
    Create and run the Rx using CLA
    '''
    parser = argparse.ArgumentParser(description="Simple FM Receiver with RTL-SDR + Scanner")
    parser.add_argument("--freq", type=float, default=100.304e6,
                        help="Requested frequency in Hz (default: 100.304e6)")
    parser.add_argument("--gain", type=float, default=25,
                        help="RF gain (default: 25)")
    parser.add_argument("--ppm", type=float, default=0.0,
                        help="PPM correction from rtl_test -p")
    parser.add_argument("--outfile", type=str, default=None,
                        help="Optional WAV output file")
    parser.add_argument("--play-audio", type=bool, default=True,
                        help="Enable live audio playback")
    parser.add_argument("--auto-fine", type=bool, default=False,
                       help="Sweeps local frequencies by 200Hz steps to look for stronger signals")

    args = parser.parse_args()

    freq_cmd = args.freq
    rx = FMRx(freq=freq_cmd,
              gain=args.gain,
              ppm=args.ppm,
              outfile=args.outfile,
              play_audio=args.play_audio,
              auto_fine=args.auto_fine)

    hw_freq = rx.src.get_center_freq()
    print(f"Requested {args.freq/1e6:.6f} MHz | Receiver tuned to {hw_freq/1e6:.6f} MHz")
    print(f"PPM={args.ppm:+.0f}, Gain={args.gain} dB")
    if args.outfile:
        print(f"Recording -> {args.outfile}")
    if args.play_audio:
        print("Playing live audio")
    print("Press Ctrl+C to stop...")

    try:
        rx.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
