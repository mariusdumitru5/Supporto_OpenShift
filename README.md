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

---

### Step 3

1. Comprendere in profondità il manifest che descrive una ResourceQuota
2. Applicare Quotas e verificarne l'effettivo funzionamento al superamento delle soglie indicate

#### ResourceQuota

Le `ResourceQuota` sono risorse di Kubernetes/OpenShift definite a livello di Namespace per limitare il consumo complessivo di risorse da parte di tutti i pod e gli oggetti presenti in quel determinato `namespace`.

In particolare stabiliscono il `soffitto massimo` per l'intero Namespace.

Le ResourceQuota non limitano solo la `memoria` e la `CPU`, ma possono controllare tre categorie principali:
- `Risorse Computazionali`: requests.cpu, limits.cpu, requests.memory, limits.memory.
- `Numero di Oggetti (Count Quotas)`: pods, services, configmaps, secrets, persistentvolumeclaims.
- `Storage`: requests.storage (spazio totale su disco che il namespace può richiedere).

##### Come funzionano le ResourceQuota nel cluster

- `Admission Control`: A ogni richiesta di creazione di un nuovo Pod, il cluster calcola la somma tra le risorse già occupate nel namespace e quelle richieste dal nuovo Pod (requests / limits).
- `Enforcement (Blocco immediato)`: Se la somma supera la soglia definita nella quota, l'`Admission Controller` rifiuta la richiesta restituendo un errore `HTTP 403 (Forbidden)`.
- `Obbligatorietà dei Limiti`: L'attivazione di una ResourceQuota su CPU o RAM impone che ogni Pod nel namespace specifichi esplicitamente le sezioni requests e limits nel proprio manifest YAML; in caso contrario, il deployment viene bloccato a prescindere.

##### quota.yaml

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota-mem-cpu-track4
  namespace: ns-track4
spec:
  hard:
    requests.cpu: "1"      
    requests.memory: "256Mi" 
    limits.cpu: "2"          
    limits.memory: "512Mi"  
    pods: "3" 
```

Per testare il funzionano possiamo fare:

1. Creo e applico la ResourceQuota
  
```bash
kubectl apply -f quota.yaml
```

2. Verifico lo stato iniziale della Quota

```bash
kubectl get resourcequota quota-mem-cpu-track4 -n ns-track4
```

3. Creo un primo Deployment valido

```bash
kubectl apply -f deployment-nginx.yaml
```

Posso verficare se il pod si avvia correttamente. Se ri-eseguo `kubectl get resourcequota`, posso vedere che la voce `USED` si è aggiornata (requests.memory: 32Mi/256Mi).

4. Forzo il fallimento della Quota

Provo a scalare il deployment a 10 repliche per superare la quota impostata (pods: "3" o requests.memory: 256Mi):

```bash
kubectl scale deployment deployment-nginx --replicas=10 -n ns-track4
```

Poi analizzare cosa è successo guardando gli eventi del sistema:

```bash
kubectl get events -n ns-track4 --field-selector reason=FailedCreate
```

Quello che osservo è un messaggio di errore generato dal `ReplicaSet` simile a questo:

```bash
Error creating: pods "deployment-nginx-..." is forbidden: exceeded quota: quota-mem-cpu-track4, requested: requests.memory=32Mi, used: 256Mi, limited: 256Mi
```

Il cluster ha bloccato la creazione dei pod in eccesso, lasciando attivi solo quelli che rientravano nel budget.