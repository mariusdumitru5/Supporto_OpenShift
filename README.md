<h1 align="center"> Supporto OpenShift </h1>

Questa repo contiene i vari esercizi e task assegnate nella track 4.

### Step 1

1. Comprendere in profondità la composizione del manifest che descrive un Deployment e un DeploymentConfig
2. Creare un deployment che installi Nginx o un'applicazione con footprint minimale

#### Deployment vs DeploymentConfig 

Le differenza principale tra `Deployment` e `DeploymentConfig` è il modo in cui viene attivato e gestito l'aggiornamento(`rollout`): 
   
   1. Il DeploymentConfig può monitorare un `ImageStream`, cioè un registro interno di OpenShift. Quando viene aggiornata l'immagine di un container, il DeploymentConfig se ne accorge in automatico e avvia un aggiornamento dei pod. 
   
   2. Il DeploymentConfig permette di eseguire comandi o pod "temporanei" in momenti precisi del ciclo di vita del deployment:
      - `Pre-hook`: Esegue un'azione prima che i nuovi pod vengano avviati (es. eseguire le migrazioni di un database). Se il pre-hook fallisce, l'aggiornamento si blocca subito.
      - `Post-hook`: Esegue un'azione dopo che l'aggiornamento è terminato con successo (es. inviare una notifica Slack o pulire la cache).

#### Nginx Deployment 

Per fare un deployment con `footprint minimale` deobbiamo dare all'applicazione le risorse minime che garantiscono comunque il corretto funzionamento. 

In generale vanno seguite le seguenti regole:
- `RAM Request`: Impostata pari al consumo medio reale dell'applicazione.
- `RAM Limit`: Impostata con un margine di sicurezza del 20-30% rispetto al picco massimo atteso. La RAM non è una risorsa comprimibile: se finisce, il pod va in crash.
- `CPU Request`: Impostata pari al consumo medio a regime.
- `CPU Limit`: Può essere lasciata `2×Request` o `3×Request` per gestire i picchi di avvio, oppure omessa del tutto per evitare il fenomeno del `Throttling` della CPU su carichi pesanti.

Quindi nel caso del deployment di un web server nginx posso mettere:

```yaml
resources:
  requests:
    memory: "32Mi" 
    cpu: "50m"
  limits:
    memory: "64Mi"
    cpu: "100m" 
```

---

### Step 2

1. Creare ROOT CA self-signed e locale
2. Creare CSR
3. Rilasciare i certificati richiesti dal CSR tramite ROOT CA creata nel punto 1

#### Creazione Root CA self-signed e locale

Per la `Root CA` dobbiamo generare prima una `chiave privata` e poi il certificato auto-firmato (self-signed).

Per generare la chiave privata possiamo usare `openssl`:

```bash
openssl genrsa -aes256 -out rootCA.key 4096
```

- `genrsa`: Algoritmo di cifratura RSA.
- `-aes256`: Cifra la chiave con password (AES-256).
- `-out rootCA.key`: Specifica il nome del file di output in cui verrà salvata la chiave privata.
- `4096`: Dimensione della chiave in bit (alta sicurezza).

Quindi alla fine di questo comando otterò la chiave privata nel file `rootCA.key`.

Per generare il certificato possiamo ancora usare `openssl`:

```bash
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 -out rootCA.crt
```

- `-x509`: Genera un certificato auto-firmato definitivo.
- `-new`: Genera una nuova richiesta/certificato da zero.
- `-nodes`: Disabilita la cifratura del certificato pubblico finale, rendendolo leggibile senza richiedere password quando viene importato dai client.
- `-key rootCA.key`: Specifica la chiave privata da utilizzare per firmare questo certificato.
- `-sha256`: Algoritmo di hash sicuro.
- `-days 3650`: Validità del certificato (10 anni).
- `-out rootCA.crt`: Specifica il nome del file di output per il certificato pubblico.

Alla fine di questo comando otterò il certifiacto pubblico `rootCA.crt` della CA locale. 


#### Creazione CSR

Il CSR (`Certificate Signing Request`) è la richiesta che un server/servizio invia alla CA per farsi firmare il certificato.

Come prima cosa devo generare la chiave privata per il server/servizio:

```bash
openssl genrsa -out server.key 2048
```

Ora possiamo generare il CSR a partire dalla chiave del server:

```bash
openssl req -new -key server.key -out server.csr
```

Otteniamo cosi `server.key` (chiave del server) e `server.csr` (il file da inviare alla CA).

#### Rilascio certificato tramite Root CA

Ora la Root CA locale riceve il CSR, lo firma e rilascia il certificato `.crt` valido per il server.

Per firmare il certificato:
```bash
openssl x509 -req -in server.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out server.crt -days 365 -sha256 
```

Otteniamo `server.crt` pronto per essere installato sul server.