from __future__ import annotations

import argparse

from .fm_receiver import FMRx

def main() -> None:
    """Create and run the Rx via CLI."""
    parser = argparse.ArgumentParser(description="Simple FM Receiver with RTL-SDR + Scanner")
    parser.add_argument("--freq", type=float, default=100.304e6, help="Frequency in Hz (default: 100.304e6)")
    parser.add_argument("--gain", type=float, default=25, help="RF gain (default: 25)")
    parser.add_argument("--ppm", type=float, default=0.0, help="PPM correction from rtl_test -p")
    parser.add_argument("--outfile", type=str, default=None, help="Optional WAV output file")
    parser.add_argument("--play-audio", action="store_true", help="Enable live audio playback")
    parser.add_argument("--auto-fine", action="store_true", help="Sweep locally to maximize signal")

    args = parser.parse_args()

    rx = FMRx(
        freq=args.freq,
        gain=args.gain,
        ppm=args.ppm,
        outfile=args.outfile,
        play_audio=args.play_audio,
        auto_fine=args.auto_fine,
    )

    hw_freq = float(rx.src.get_center_freq())
    print(f"Requested {args.freq/1e6:.6f} MHz | Receiver tuned to {hw_freq/1e6:.6f} MHz")
    print(f"PPM={args.ppm:+.0f}, Gain={args.gain} dB")
    if args.outfile:
        print(f"Recording -> {args.outfile}")
    if args.play_audio:
        print("Playing live audio")
    print("Press Ctrl+C to stop…")

    try:
        rx.run()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()