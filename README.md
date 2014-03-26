download-cleanup
================

Transmission download folder cleanup utility.

You must have `incomplete-dir-enabled` in your Transmission config (for now).


Show unreferenced files
-----------------------

Just run it:

    % ./download-cleanup
    File1
    File2
    ...


Move unreferenced files elsewhere
---------------------------------

Add `--move-to ~/Done`:

    % ./download-cleanup --move-to ~/Done
    INFO: Moving u'/home/ch/Downloads/File1' -> u'/home/ch/Done/File1' ...
    INFO: Moving u'/home/ch/Downloads/File2' -> u'/home/ch/Done/File2' ...
    ...


Additional options
------------------

See `--help`:

    % ./download-cleanup --help
    usage: download-cleanup [-h] [--debug] [--transmission-dir TRANSMISSION_DIR]
                            [--download-dir DOWNLOAD_DIR] [--move-to MOVE_TO]
                            [--ignore IGNORE]

    optional arguments:
      -h, --help            show this help message and exit
      --debug
      --transmission-dir TRANSMISSION_DIR
                            Transmission state/config dir (auto-detected)
      --download-dir DOWNLOAD_DIR
                            Download directory (auto-detected)
      --move-to MOVE_TO     If given, leftover files/dirs are moved to this path
      --ignore IGNORE       Ignore files/directories matching this pattern

Debugging
---------

Try `--debug`.

Most error cases are untested. Non-Linux or old Linux platforms are untested.
