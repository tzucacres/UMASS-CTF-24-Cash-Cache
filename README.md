# Relatório Técnico — Cash Cache (UMASS CTF 2024)

**Autores:** Arthur Hugo Barros Gaia · Felipe Ivo da Silva · Nathalia Cristina Santos · Thiago Zucarelli Crestani · Wilson de Camargo Vieira  
**Versão:** 1.0  
**Uso:** documento técnico para reprodução em ambiente controlado (CTF / laboratório). Não execute contra sistemas sem autorização. :contentReference[oaicite:1]{index=1}

---

## Sumário
1. [Resumo](#resumo)  
2. [Introdução](#introdução)  
3. [Objetivo](#objetivo)  
4. [Conceitos técnicos relevantes](#conceitos-técnicos-relevantes)  
5. [Comportamento do serviço (resumo observacional)](#comportamento-do-servi%C3%A7o-resumo-observacional)  
6. [Estratégia de exploração — passo a passo (alto nível)](#estrat%C3%A9gia-de-explora%C3%A7%C3%A3o---passo-a-passo-alto-n%C3%ADvel)  
7. [PoCs / Códigos comentados (trechos essenciais)](#pocs--c%C3%B3digos-comentados-trechos-essenciais)  
   - 7.1 [Payload HTTP smuggling (raw)](#payload-http-smuggling-raw)  
   - 7.2 [Payload de desserialização (Python — `pickle` PoC)](#payload-de-desserializa%C3%A7%C3%A3o-python--pickle-poc)  
   - 7.3 [Sequência de execução (shell)](#sequ%C3%AAncia-de-execu%C3%A7%C3%A3o-shell)  
8. [Análise de impacto (CIA)](#an%C3%A1lise-de-impacto-cia)  
9. [Mitigações e mapeamento OWASP (priorizadas)](#mitiga%C3%A7%C3%B5es-e-mapeamento-owasp-priorizadas)  
10. [Detecção e monitoramento (o que logar / alertar)](#detec%C3%A7%C3%A3o-e-monitoramento-o-que-logar--alertar)  
11. [Plano de correção imediato (primeiras 72 horas)](#plano-de-corre%C3%A7%C3%A3o-imediato-primeiras-72-horas)  
12. [Lições aprendidas e recomendações finais](#li%C3%A7%C3%B5es-aprendidas-e-recomenda%C3%A7%C3%B5es-finais)  
13. [Referências](#refer%C3%AAncias)  

---

## Resumo
Relatório conciso documentando um vetor combinado observado em laboratório: **HTTP request smuggling** que entrega um payload binário a um componente que realiza **desserialização insegura**, permitindo execução de código e exfiltração de segredo (flag). O documento contém descrição técnica, passos de exploração em alto nível, PoCs comentados, análise de impacto e recomendações práticas mapeadas ao OWASP Top 10. :contentReference[oaicite:2]{index=2}

---

## Introdução
Este relatório descreve a análise técnica realizada em ambiente controlado (CTF). O objetivo é explicar, de forma didática e acionável, o vetor de exploração que levou à recuperação da prova, além de propor medidas mitigatórias e de detecção aplicáveis em ambientes produtivos. :contentReference[oaicite:3]{index=3}

---

## Objetivo
- Demonstrar a técnica combinada (request smuggling + insecure deserialization) em ambiente controlado;  
- Documentar a estratégia de exploração e apresentar PoCs comentados para fins educativos;  
- Propor medidas de correção, prevenção e detecção alinhadas ao OWASP. :contentReference[oaicite:4]{index=4}

---

## Conceitos técnicos relevantes
- **Request Smuggling:** divergência na interpretação de uma mesma requisição entre proxy/load-balancer e backend (ex.: `Content-Length` vs `Transfer-Encoding`) que possibilita que uma requisição “extra” chegue ao backend. :contentReference[oaicite:5]{index=5}  
- **Insecure Deserialization:** desserializar dados não confiáveis (ex.: objetos binários que executam código quando reconstruídos) conduz a execução remota de código (RCE). :contentReference[oaicite:6]{index=6}  
- **Exfiltração via serviços internos:** após RCE, leitura de ficheiros/keys e gravação em cache/DB interno facilita recuperação pelo atacante. :contentReference[oaicite:7]{index=7}

---

## Comportamento do serviço (resumo observacional)
- Serviço aceita tráfego HTTP e possui componente que processa dados binários/serializados.  
- Existe fluxo funcional em que um payload malformado, se entregue ao backend, causa desserialização de um objeto controlado pelo atacante.  
- Um fluxo de exfiltração simples (ler recurso interno → gravar em local que o atacante possa ler) é suficiente para comprovar a exploração. :contentReference[oaicite:8]{index=8}

---

## Estratégia de exploração — passo a passo (alto nível)
1. Preparar ambiente de teste (serviço + dependências em sandbox).  
2. Construir requisição CRLF-crafted para *smuggle* (encaixar uma segunda requisição no stream).  
3. Inserir no corpo da requisição um payload serializado malicioso (ex.: `pickle` com código a executar).  
4. Enviar requisição ao ponto que diferencia parsing entre camadas para que a requisição oculta seja processada pelo backend.  
5. Após desserialização/execução, recuperar o resultado (ex.: leitura de cache/DB onde o payload gravou o segredo).  
6. Registrar evidências (logs, saída, artefatos) para documentação. :contentReference[oaicite:9]{index=9}

---

## PoCs / Códigos comentados (trechos essenciais)

**Aviso:** os exemplos abaixo são didáticos e devem ser executados somente em ambiente controlado. Não use contra sistemas sem autorização. :contentReference[oaicite:10]{index=10}

### Payload HTTP smuggling (raw)
```http
POST /some-proxy-path HTTP/1.1
Host: victim.local
Connection: keep-alive
Content-Length: 137
Content-Type: application/x-www-form-urlencoded

<dados-legítimos...>

POST /internal-endpoint HTTP/1.1
Host: backend.local
Content-Length: 72
Content-Type: application/octet-stream

<-- aqui vai o corpo binário (payload serializado) -->
