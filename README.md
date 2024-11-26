# Foam
Foam is a command-line tool for tracking and restoring the state of folders. It can be used as a lightweight alternative
to git tracking for managing folder contents during development or testing workflows.

## USAGE:
    foam track [options] [folders...]
        --list       List currently tracked folders
        --undo       Clear all tracked folders
        [folders...] Specify one or more folders to track

    foam reset
        Reset all tracked folders to their previously saved state.

## DESCRIPTION:
    - 'track': Tracks the current state of specified folders. You can list or clear tracked folders using options.
    - 'reset': Resets folders to the last tracked state, restoring all files and directories to their original condition.

## EXAMPLES:
    Track folders:
        foam track /path/to/folder1 /path/to/folder2

    List tracked folders:
        foam track --list

    Clear all tracked folders:
        foam track --undo

    Reset folders:
        foam reset
