import logging
from ui import DraggableApp

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    app = DraggableApp()
    app.mainloop()