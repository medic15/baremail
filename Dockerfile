FROM python:2.7-alpine

WORKDIR /

#COPY requirements.txt ./
#RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ ".src/baremail.py", "../config/standard_port.json" ]
