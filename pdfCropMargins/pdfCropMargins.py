#!/usr/bin/python

"""

 This is the initial starting script, but it is just calls main2, which does the
 real work.  Its only purpose is to handle errors and make sure that any temp
 directories are cleaned up.

"""


from __future__ import print_function, division
import sys

def main():
    """Run main2, catching any exceptions and cleaning up the temp directories."""
    def cleanupIgnoringKeyboardInterrupt():
        """Some people like to hit multiple ^C chars; ignore them and call again."""
        try:
            ex.cleanupAndExit(exitCode)
        except KeyboardInterrupt: # Some people hit multiple ^C chars, kills cleanup.
            cleanupIgnoringKeyboardInterrupt()
        except SystemExit:
            pass

    exitCode = 0
    try:
        # Import here so any ugly traceback is caught on ^C by user.
        import mainPdfCropMargins
        import external_program_calls as ex
        mainPdfCropMargins.main2()
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

