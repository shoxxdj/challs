FROM php:8.1-apache

COPY ./code/ /var/www/html/
RUN chown -R www-data:www-data /var/www
# Contenu du flag (modifiable à la construction)
ARG FLAG_CONTENT="HCKDMB{medium_pop_chain}"

# Crée /flag, appartient à root, lisible par tous (rw-r--r--)
RUN printf '%s\n' "$FLAG_CONTENT" > /flag \
    && chown root:root /flag \
    && chmod 644 /flag


EXPOSE 80
