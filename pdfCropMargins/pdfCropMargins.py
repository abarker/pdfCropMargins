#!/usr/bin/python

"""

 This is the initial starting script, but it is just calls mainCrop, which does
 the real work.  Its only purpose is to handle errors and make sure that any
 temp directories are cleaned up.  It tries to gracefully handle ^C characters
 from the user (KeyboardInterrupt) to stop the program and clean up.

"""

from __future__ import print_function, division
import sys


def main():
    """Run main, catching any exceptions and cleaning up the temp directories."""
    def cleanupIgnoringKeyboardInterrupt():
        """Some people like to hit multiple ^C chars; ignore them and call again."""
        for i in range(20): # Give up after 20 tries.
            try:
                cleanupAndExit(exitCode) # Use the global one for now TODO
            except KeyboardInterrupt: # Some people hit multiple ^C chars, kills cleanup.
                continue
            except SystemExit:
                pass

    cleanupAndExit = sys.exit # Function to do cleanup and exit.
    exitCode = 0

    # Imports are done here inside the try block so some ugly (and useless)
    # traceback info is avoided on user's ^C (KeyboardInterrupt).
    try:
        import external_program_calls as ex # Creates the tmp dir as side effect.
        cleanupAndExit = ex.cleanupAndExit # Now delete temp dir, too.
        import mainPdfCropMargins # Imports external_program_calls, don't do first.
        mainPdfCropMargins.mainCrop() # Run the actual program.
    except KeyboardInterrupt:
        print("\nGot a KeyboardInterrupt, cleaning up and exiting...\n",
              file=sys.stderr)
    except SystemExit:
        print()
    except:
        # Echo back the unexpected error so the user can see it.
        print("Unexpected error: ", sys.exc_info()[0], file=sys.stderr)
        print("Error message   : ", sys.exc_info()[1], file=sys.stderr)
        print()
        import traceback
        traceback.print_tb(sys.exc_info()[2])
        exitCode = 1
        #raise # Re-raise the error.
    finally:
        cleanupIgnoringKeyboardInterrupt()
    return


##
## Run as a script.
##


if __name__ == "__main__":
    main()

