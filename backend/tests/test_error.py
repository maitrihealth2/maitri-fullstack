from core.logger.terminal import CommandCenter

def bad_function():
    return 1 / 0

if __name__ == "__main__":
    CommandCenter.start_dashboard()
    try:
        bad_function()
    except Exception as e:
        CommandCenter.log_error(f"Failed in logic: {e}", exc=e)
