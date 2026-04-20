# ✈️ Aviation Incident Intelligence Pipeline

A robust, multi-stage data engineering project designed to scrape, structure, and enrich a massive dataset of global aviation incidents (20,000+ records). This tool bridges the gap between raw historical archives and structured JSON data for further analytics.

## 🚀 Key Features

* **Advanced Anti-Bot Bypass:** Leveraged **Playwright** to navigate protected web environments, handling dynamic content and security headers that bypass standard HTTP client blocks.
* **Massive Scale:** Successfully extracted and processed a **28MB+ JSON dataset** covering incidents from 1940 to the present.
* **Media Enrichment:** Integrated a specialized module to match incident records with high-quality imagery from **JetPhotos**, creating a comprehensive visual-technical archive.
* **High Performance:** Optimized data collection using **Asyncio** and **Aiohttp**, significantly reducing the time required for media-heavy enrichment tasks.
* **Data Integrity:** Implemented custom logic for parsing inconsistent historical records and normalizing data formats across 80 years of history.

## 🛠 Tech Stack

* **Language:** Python 3.10+
* **Automation/Scraping:** Playwright, BeautifulSoup4, Requests
* **Asynchronous Processing:** Asyncio, Aiohttp
* **Data Storage:** JSON (Optimized for NoSQL import)

## 📁 Project Architecture

The system is built with a modular approach to ensure flexibility and fault tolerance:

* `aviacrashes.py` – The main engine for extracting primary incident data.
* `add_photo.py` – Specialized module for bypassing security protections and scraping dynamic elements.
* `aviacrashes_async_photo.py` – High-speed asynchronous script for matching incidents with aircraft photography.
* `/data` – Contains a sample of the 28MB dataset (Full dataset available upon request).

## 📊 Business Value
This pipeline transforms fragmented web data into a clean, machine-learning-ready format. It can be used for aviation safety trend analysis, insurance risk assessment, or historical research.