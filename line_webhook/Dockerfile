# ใช้ Python base image
FROM python:3.11-slim

# ติดตั้ง Node.js และ npm
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ตรวจสอบว่า npx ติดตั้งถูกต้อง
RUN which npx && npx --version

# ตั้งค่า working directory
WORKDIR /app

# Copy requirements และติดตั้ง Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy โค้ดทั้งหมด
COPY . .

# ติดตั้ง LINE Bot MCP Server package
RUN npm install -g @line/line-bot-mcp-server

# ตั้งค่า environment variables
ENV PYTHONPATH=/app
ENV PORT=8080
ENV NPX_PATH=/usr/bin/npx
ENV PATH="/usr/bin:${PATH}"

# ตรวจสอบว่า npx ทำงานได้
RUN which npx && npx --version

# Expose port
EXPOSE 8080

# รัน application
CMD ["python", "main.py"]