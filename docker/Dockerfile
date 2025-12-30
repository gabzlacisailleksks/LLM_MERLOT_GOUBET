
FROM ubuntu:22.04
RUN useradd -m appuser
USER appuser
RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://example.com/install.sh | sh
CMD ["bash"]
