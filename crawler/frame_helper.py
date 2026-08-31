async def get_main_frame(page):

    for frame in page.frames:

        if frame.name == "mainFrame":

            return frame

    return None