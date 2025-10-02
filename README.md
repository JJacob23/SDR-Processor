# SDR-Processor
#Setup
See environment.yml for conda environment
Using RTL with nooelec R820T demodulator for testing.

# Testing
Test tunings outside of app with rtl_fm such as:
rtl_fm -f 101.1M -M wbfm -s 200000 -r 48000 -g 25 -E deemp -F 9 - | ffplay -f s16le -ar 48000 -

Run program with:
python fm_receiver.py [-h for options]

# Station quick reference
98.700e6 -> comes in clear: WMZQ country
101.1e6 -> intermittent: DC variety
100.304e6 -> clear : classic rock
