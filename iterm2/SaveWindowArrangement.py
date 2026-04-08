import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if not window:
        return

    name = await window.async_get_variable("titleOverride")

    if not name:
        alert = iterm2.TextInputAlert(
            "Save Window as Arrangement",
            "Enter a name for this arrangement:",
            "My Arrangement",
            ""
        )
        name = await alert.async_run(connection)

    if name:
        await window.async_save_window_as_arrangement(name)

iterm2.run_until_complete(main)
