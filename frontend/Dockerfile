FROM node:20-alpine AS build

WORKDIR /app

COPY package.json yarn.lock* ./
RUN yarn install --network-timeout 600000

COPY . .
ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
# SEGURANÇA (auditoria, item S5): com o runtime do webpack inline no HTML
# (padrão do CRA), o CSP do nginx precisaria de script-src 'unsafe-inline' —
# o que anularia a proteção contra XSS que o CSP existe para dar.
ENV INLINE_RUNTIME_CHUNK=false
# SEGURANÇA (auditoria, item S9): source map expõe o código-fonte original
# (inclusive comentários e caminho dos arquivos) para qualquer visitante que
# abra o DevTools — sem necessidade em produção.
ENV GENERATE_SOURCEMAP=false
RUN yarn build
# Trava: se sobrar algum .map (ex.: de uma dependência que gera o seu
# próprio arquivo, fora do controle de GENERATE_SOURCEMAP), o build falha em
# vez de publicar código-fonte por engano.
RUN ! find build -name '*.map' | grep -q .

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
