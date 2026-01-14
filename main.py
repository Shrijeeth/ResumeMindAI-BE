import logging
import warnings

import uvicorn
from dotenv import load_dotenv

from configs import get_settings

load_dotenv()
warnings.simplefilter(action="ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
