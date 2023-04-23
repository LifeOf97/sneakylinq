# Django Up

A template to quickly get up and coding your [Django](https://www.djangoproject.com/) apps.


## The Why, What & How

*   ### Why Djangoup ?

    As a Django developer, while starting a new project, i find myself doing the same thing over and over again. That is, setting up a docker environment for development, installing django, running the ```startproject``` command and more.

*   ### What will Djangoup accomplish ?

    The goal of this ```repo``` is to instantly spin up a django environment for development, with the following as key factors

    * Consistency.
    * Simplicity.
    * Ease of use.


*   ### How to use Djangoup
    
    At this point, it is safe to say you are familiar with [Python](https://www.python.org/) & [Django](https://www.djangoproject.com/).

    > Make sure to have docker and docker compose installed on your system, this will be needed as this project is designed to run in a docker environment. Please refer to [Docker](https://docs.docker.com/) to get started with docker if you need to.

    * Clone this repo
        ```cmd
        $ git clone https://github.com/realestKMA/djangoup.git
        ```
    * Create a virtual environment:
        ```cmd 
        $ python -m venv venv
        ```
    * Install dependencies in the ```requirements``` file  using ```pip```:
       ```cmd
       $ pip install -r requirements.txt
       ```

    * create an ```.env``` file with data from the ```.env.sample``` and fill the required details:
        ```cmd
        $ cp .env.sample .env
        ```
    * Build the docker compose file using the dev yaml file:
        ```cmd
        $ docker compose -f docker-compose.dev.yml build
        ```
    * Bring up the docker compose file and start coding:
        ```cmd
        $ docker compose -f docker-compose.dev.yml up
        ```

    Your project is now up and ready for development, you can now access it by visiting [http://127.0.0.1:8000](). Changes made while you code will automatically reflect on the docker instance.


## Settings

Please note, the settings module has been split into three seperate modules as per my preferred use case inside the [settings](https://github.com/realestKMA/djangoup/tree/main/src/settings) folder in the [src](https://github.com/realestKMA/djangoup/tree/main/src) project. These are

*   ### base module
    
    This module houses settings that span both development and production environment.

*   ### development module
    
    This module imports all settings from the ```base``` module. Here, i provide and/or make changes that is required for my development environment.

*   ### production module
    
    This module also imports all settings from the ```base``` module. Here, i provide and/or make changes that is required for my production environment.

## Database

To get up and coding your django apps, a ```postgres``` database has also been provided in the docker compose file. This will serve as the default database as specifeid in the [development.py](https://github.com/realestKMA/djangoup/blob/main/src/settings/development.py) & [production.py](https://github.com/realestKMA/djangoup/blob/main/src/settings/production.py) settings module. 

## Scripts

Few convenient ```bash``` scripts are provided

## Docker

This folder contains the docker files per service if explicitly required.

## Please
Make changes that suite your need. Thanks.
