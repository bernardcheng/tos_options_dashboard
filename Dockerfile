# Select base python image
FROM python:3.7

# Define working directory in the Docker image
WORKDIR /dashboard_app

# Copy over required files into working directory (src, requirements.txt, assets)
COPY requirements.txt requirements.txt
COPY src /dashboard_app/src
COPY assets /dashboard_app/assets

# Add the main dashboard script and config file to working directory of Docker Image
ADD dashboard.py .
ADD config.yml .

# Run installation of python libraries in Docker Image
RUN pip3 install -r requirements.txt

# Expose port specified in dashboard script
EXPOSE 8050

# Opening cmd when starting Image
CMD ["python", "./dashboard.py", "--docker"]