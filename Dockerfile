FROM python:3.8.2

ADD /requirements.txt project/requirements.txt
ADD /app/api/config.txt project/app/api/config.txt
ADD /app/api/server.py project/app/api/server.txt
ADD /app/api/utils.py project/app/api/utils.py
ADD /app/db/client/client.py project/db/client/client.py
ADD /app/db/interaction/interaction.py project/db/interaction/interaction.py
ADD /app/db/models/models.py project/db/models/models.py
ADD /app/db/exceptions.py project/app/db/exceptions.py

RUN pip3.8 install -r /project/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/project/app"
WORKDIR /project

EXPOSE 5005

CMD ["python", "./app/api/server.py", "--config=./app/api/config.txt"]