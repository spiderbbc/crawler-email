from requests_html import HTMLSession
from urllib.parse import urlparse, urljoin
from validate_email import validate_email
from bs4 import BeautifulSoup
import colorama
import re


# init the colorama module
colorama.init()
# globla variables to print terminal
GREEN = colorama.Fore.GREEN
RED = colorama.Fore.RED
GRAY = colorama.Fore.LIGHTBLACK_EX
RESET = colorama.Fore.RESET
# email regex
EMAIL_REGEX = r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""
# initialize the set of links (unique links)
internal_urls = set()
external_urls = set()
emails = set()

total_urls_visited = 0


def is_valid(url):
    """
    validate if it is a url
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def get_all_website_links(url):
    """
    Returns all URLs
    params:
            url (url): hiper enlace para realizar scraping de todos los links.
    """
    # all URLs of `url`
    urls = set()
    # domain name of the URL without the protocol
    domain_name = urlparse(url).netloc
    # initialize an HTTP session
    session = HTMLSession()
    # make HTTP request & retrieve response
    response = session.get(url)

    if response.status_code == 200:
        # execute Javascript
        try:
            response.html.render(timeout=10)
        except:
            pass
        soup = BeautifulSoup(response.html.html, "html.parser")

        for a_tag in soup.findAll("a"):
            href = a_tag.attrs.get("href")
            if href == "" or href is None:
                # href empty tag
                continue
            # join the URL if it's relative (not absolute link)
            href = urljoin(url, href)
            parsed_href = urlparse(href)
            # remove URL GET parameters, URL fragments, etc.
            href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path
            if not is_valid(href):
                # not a valid URL
                continue
            if href in internal_urls:
                # already in the set
                continue
            if domain_name not in href:
                # external link
                if href not in external_urls:
                    print(f"{GRAY}[!] External link: {href}{RESET}")
                    external_urls.add(href)

                continue
            print(f"{GREEN}[*] Internal link: {href}{RESET}")
            urls.add(href)
            internal_urls.add(href)
            # if internal link get the emails
            get_all_email(href)

    return urls


def get_all_email(href):
    """
        Crawls a web page and extracts all emails.
        params:
            href (string): hiper enlace para realizar scraping en a[href^=mailto] y en el Html.
    """
    if href not in internal_urls:
        # initiate an HTTP session
        session = HTMLSession()
        # get the HTTP Response
        r = session.get(href)

        if r.status_code == 200:
            # for JAVA-Script web pages
            try:
                r.html.render(timeout=10)
            except:
                pass

            soup = BeautifulSoup(r.html.html, "html.parser")
            # filter for mailto links
            links = soup.select('a[href^=mailto]')

            for link in links:
                hypertext = link['href']
                try:
                    # split and get the last one
                    email = hypertext.split(':')[-1]
                    print(f"{RED}[*] Email: {email} in {href}{RESET}")
                except ValueError:
                    pass
                # put on set list
                if email not in emails and validate_email(email_address=email, check_regex=True, check_mx=False,use_blacklist=True, debug=False):
                    emails.add(email)

            # looking on the text
            for re_match in re.finditer(EMAIL_REGEX, r.html.raw_html.decode()):
                print(f"{RED}[*] Email: {re_match.group()} in {href}{RESET}")
                if re_match.group() not in emails and validate_email(email_address=re_match.group(),
                                                                     check_regex=True, check_mx=True,
                                                                     use_blacklist=True, debug=False):
                    emails.add(re_match.group())



async def crawl(url, max_urls=50):
    """
    Crawls a web page and extracts all links.
    params:
        max_urls (int): cantidad de URL máximas para rastrear, el valor predeterminado es 50.
    """
    global total_urls_visited
    total_urls_visited += 1
    links = get_all_website_links(url)
    for link in links:
        if total_urls_visited > max_urls:
            break

        return crawl(link, max_urls=max_urls)


if __name__ == "__main__":
    import os
    import argparse
    import asyncio
    from signal import SIGINT, SIGTERM

    parser = argparse.ArgumentParser(
        description="Herramienta de Extracción de Hiper Enlaces y Correos Electronicos")
    parser.add_argument("url", help="La Url para extraer los Hiper Enlaces y Correos Electronicos")
    parser.add_argument(
        "-m", "--max-urls", help="Numeros Maximo de URLs a hacer el Scrapping, por defecto es 50.", default=50, type=int)

    args = parser.parse_args()
    # get url from terminal
    url = args.url
    # get -m from terminal
    max_urls = args.max_urls
    # extract email from root url
    get_all_email(url)

    # look up all the links
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(crawl(url, max_urls=max_urls))
    loop.add_signal_handler(SIGINT, main_task.cancel)
    loop.add_signal_handler(SIGTERM, main_task.cancel)

    try:
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        print("Received exit, exiting")


    # get the domain to name txt
    domain_name = urlparse(url).netloc

    # if folder not exits, then create
    if not os.path.isdir('links') and not os.path.isdir('emails'):
        try:
            os.makedirs('links')
            os.makedirs('emails')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    # save the internal links to a file
    with open(f"links/{domain_name}_internal_links.txt", "w") as f:
        for internal_link in internal_urls:
            print(internal_link.strip(), file=f)

    # save the external links to a file
    with open(f"links/{domain_name}_external_links.txt", "w") as f:
        for external_link in external_urls:
            print(external_link.strip(), file=f)


    # save the emails in to the file
    if not emails:
        with open(f"emails/{domain_name}_internals_emails.txt", "w") as f:
            for email in emails:
                print(email.strip(), file=f)

    # print results
    print("[+] Total Internal links:", len(internal_urls))
    print("[+] Total External links:", len(external_urls))
    print("[+] Total Emails:", len(emails))
    print("[+] Total URLs:", len(external_urls) + len(internal_urls))
