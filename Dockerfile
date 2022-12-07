# start by pulling the python image
FROM ubuntu
MAINTAINER Roopam Verma

RUN apt-get update && apt-get install -y software-properties-common gcc && \
    add-apt-repository -y ppa:deadsnakes/ppa

RUN apt-get install -y python3.9 python3-distutils python3-pip python3-apt curl vim

# copy the requirements file into the image
COPY ./app/requirements.txt /app/requirements.txt


# switch working directory
WORKDIR /app


# install the dependencies and packages in the requirements file
RUN pip3.9 install -r requirements.txt



# copy every content from the local file to the image
COPY ./app /app



# configure the container to run in an executed manner
ENTRYPOINT [ "python3.9" ]



CMD ["/app/app.py" ]
