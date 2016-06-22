# hpsdrtool

Setup (adds the command globally):

    sudo make install

Usage:

    hpsdrtool <hpsdr_metis_ip> [--freq <freq_in_hz>] [--preamp] [--no-iq-output]

It will output the 24 bit, signed I/Q samples to the standard output (unless `--no-iq-output` is specified, as then it just prints some debug information).
