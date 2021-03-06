import requests
import tabula
import io
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PyPDF2 import PdfFileReader
from config import app_logger
from datetime import datetime


class RobScraper:
    """
    The RobScraper can be used to scrape a pdf-file containing information about rescued seal pups and save
    it to a pandas dataframe. The pdf can be accessed either on the website of Seehundstation Friedrichskoog or in a
    downloaded pdf that is stored in the local file system.
    """
    def find_rob(self) -> list:
        """
        Finds the link to the current pdf-file of rescued seal pups.
        :return: (list) A list of links that are likely to contain the current pdf-file of rescued seal pups. Ideally,
        the list is of length 1.
        """
        url = "https://www.seehundstation-friedrichskoog.de/aktuelle-saison/"
        read = requests.get(url)
        html_content = read.content
        soup = BeautifulSoup(html_content, "html.parser")

        list_of_links = []
        for a in soup.find_all("a", href=True):
            mystr = a["href"]
            if mystr.find("/wp-content/heuler/") != -1 and mystr[-4:] == ".pdf":
                list_of_links.append(urljoin(url, mystr))

        assert len(list_of_links) > 0, app_logger.error("Found no link.")
        if len(list_of_links) > 1:
            app_logger.warning("Found more than 1 link. Make sure you parse the correct file!")

        self.link_to_rob_ = list_of_links
        return self.link_to_rob_

    def scrape_rob(self, index: int = 0, path_to_raw: str = None) -> pd.DataFrame:
        """
        Scrapes the current pdf-file of rescued seal pups and saves it in a pandas.DataFrame
        :param index: (int) The index in list self.link_to_rob_ that identifies the link to the pdf to scrape from
        :param path_to_raw: (str) Local path that identifies the link to the pdf to scrape from
        :return: (pd.DataFrame) A pandas.DataFrame that contains information about rescued seal pups
        """
        try:
            if path_to_raw is None:
                link_to_rob = self.link_to_rob_[index]
                read = requests.get(link_to_rob)
                pdf_obj = io.BytesIO(read.content)
            else:
                link_to_rob = path_to_raw
                pdf_obj = open(path_to_raw, 'rb')
            pdf_file_reader = PdfFileReader(pdf_obj)
            total_pages = pdf_file_reader.numPages
            date = pdf_file_reader.documentInfo["/ModDate"]
            pdf_obj.close()
            self.date_ = datetime.strptime(date.replace("'", ""), "D:%Y%m%d%H%M%S%z")
            df_rob = pd.concat([tabula.read_pdf(link_to_rob, pages="1", encoding="cp1252",  # Page 1
                                                area=[10, 0, 95, 100], relative_area=True, multiple_tables=False,
                                                pandas_options={"header": None,
                                                                "names": ["Fundort", "Einlieferungsdatum", "Tierart",
                                                                          "Aktuell"]})[0],
                                tabula.read_pdf(link_to_rob, pages="2-" + str(total_pages),
                                                encoding="cp1252",  # Remaining pages
                                                area=[5, 0, 95, 100], relative_area=True, multiple_tables=False,
                                                pandas_options={"header": None,
                                                                "names": ["Fundort", "Einlieferungsdatum", "Tierart",
                                                                          "Aktuell"]})[0]]).reset_index(drop=True)

            df_rob["Einlieferungsdatum"] = pd.to_datetime(df_rob["Einlieferungsdatum"], format="%d.%m.%Y")
            self.df_rob_ = df_rob
            return self.df_rob_
        except AttributeError:
            app_logger.exception(
                "The RobScraper has no attribute link_to_rob_. "
                "Have you run function find_rob already?")
        except FileNotFoundError:
            app_logger.exception(
                "The RobScraper cannot find the file specified in attribute local_path_to_rob. "
                "Are you sure the file exists?")
        except requests.exceptions.MissingSchema:
            app_logger.exception(
                "The URL stored in RobScraper attribute link_to_rob_ is invalid. "
                "Have you run function find_rob already?")
        except Exception:
            app_logger.exception("Unexpected exception occurred.")


def main():
    rob_scraper = RobScraper()
    rob_scraper.find_rob()
    rob_scraper.scrape_rob()
    print(rob_scraper.date_)


if __name__ == "__main__":
    main()
