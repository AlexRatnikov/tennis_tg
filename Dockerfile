# Use the official Python image from the Docker Hub
FROM python:3.12

# Set the working directory
WORKDIR /app
ENV HOST 0.0.0.0

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Local run check commands:
# docker build -t tennis_tg .
# docker run -d -p 8080:8080 --name tennis-tg-container tennis_tg

# Run app.py when the container launches
CMD ["gunicorn", "bot:application", "--workers", "3", "--bind", "0.0.0.0:8080"]
