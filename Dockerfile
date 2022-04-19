# Select base python image
FROM python:3.7

# Define working directory in the Docker image
WORKDIR /dashboard_app

# Copy over required files into working directory (src, requirements.txt, assets)
COPY requirements.txt requirements.txt
COPY lib /dashboard_app/lib
COPY assets /dashboard_app/assets
COPY dashboard_app /dashboard_app/dashboard_app

# Add the main dashboard script and config file to working directory of Docker Image
ADD dashboard.py .

# Set up environment variable (TOS API Key) in Docker
ARG api_key = ENTER_API_KEY_HERE
ENV TOS_API_KEY=$api_key

# Run installation of python libraries in Docker Image
RUN pip3 install -r requirements.txt

# Expose port specified in dashboard script
EXPOSE 8050

# Opening cmd when starting Image
CMD ["python", "./dashboard.py", "--docker"]