# OpcSImulator

Simulateur de **serveur OPC UA** piloté par une liste de points décrite en **JSON**, dans l'esprit de l'interface d'un automate **Wago PFC100** (entrées/sorties TOR et analogiques, informations device...).

## Installation

```bash
pip install -r requirements.txt
```

## Démarrage

```bash
python main.py --config config/points.json
# ou avec un endpoint précis :
python main.py --config config/points.json --endpoint opc.tcp://127.0.0.1:4840
```

Le serveur écoute par défaut sur `opc.tcp://0.0.0.0:4840` (NoSecurity).

## Format du fichier JSON

```json
{
  "server": {
    "endpoint": "opc.tcp://0.0.0.0:4840",
    "application_name": "Wago PFC100 Simulator",
    "application_uri": "urn:wago:pfc100:simulator",
    "namespace": "http://wago.com/pfc100/simulator",
    "root_object": "PFC100"
  },
  "points": [
    {
      "name": "AnalogInputs.AI0",
      "datatype": "Float",
      "value": 20.0,
      "unit": "degC",
      "min": -20.0,
      "max": 120.0,
      "writable": true,
      "description": "Entree analogique 0",
      "nodeid": "ns=2;s=mon.node.explicite",
      "simulation": { "mode": "sine", "amplitude": 25.0, "period_s": 30.0, "interval_ms": 500 }
    }
  ]
}
```

### Champs `server`

| Champ | Défaut | Description |
|---|---|---|
| `endpoint` | `opc.tcp://0.0.0.0:4840` | URL d'écoute du serveur |
| `application_name` | `OPC UA Simulator` | Nom affiché du serveur |
| `application_uri` | `urn:opcua:simulator` | URI d'application |
| `namespace` | `http://opcua.simulator.local` | URI du namespace des points (sera `ns=2`) |
| `root_object` | `Simulator` | Objet racine créé sous `Objects` |

### Champs d'un point

| Champ | Obligatoire | Description |
|---|---|---|
| `name` | oui | Chemin du point, les `.` créent des dossiers (ex: `AnalogInputs.AI0` → `PFC100/AnalogInputs/AI0`). Par défaut le NodeId string est ce chemin (`ns=2;s=AnalogInputs.AI0`) |
| `datatype` | non* | Type OPC UA (voir liste ci-dessous). `*` déduit de `value` si absent |
| `value` | non | Valeur initiale |
| `nodeid` | non | NodeId explicite (ex: `ns=2;s=...` ou identifiant string) |
| `writable` | non | `true` par défaut ; `false` = lecture seule pour les clients |
| `description` | non | Description OPC UA du noeud |
| `unit` / `min` / `max` | non | Ajoutés comme properties `Unit`, `Min`, `Max` du noeud |
| `simulation` | non | Animation de la valeur (voir ci-dessous) |

Types supportés : `Boolean`, `SByte`, `Byte`, `Int16`, `UInt16`, `Int32`, `UInt32`, `Int64`, `UInt64`, `Float`, `Double`, `String`, `DateTime`.

### Modes de `simulation`

| Mode | Effet | Paramètres utiles |
|---|---|---|
| `constant` | Valeur fixe (défaut) | — |
| `random` | Valeur aléatoire à chaque intervalle | `min`, `max` (sinon `min`/`max` du point, sinon 0..1 / 0..100 / bool au hasard) |
| `sine` | `value + amplitude * sin(2*pi*t/period_s)` | `amplitude`, `period_s` |
| `increment` / `decrement` | `valeur +/- step` | `step`, `wrap` (reboucle), `min` |
| `toggle` | Inverse un Boolean | — |
| `cycle` | Parcourt une liste de valeurs | `values: [...]` |

`interval_ms` (défaut 1000, min 50) = période de mise à jour.

## Exemple de client

```bash
python examples/client_example.py --url opc.tcp://127.0.0.1:4840 \
    --namespace http://wago.com/pfc100/simulator
```

Lecture / écriture depuis un autre client (exemple avec `asyncua`) :

```python
from asyncua import Client, ua

async with Client(url="opc.tcp://127.0.0.1:4840") as client:
    idx = await client.get_namespace_index("http://wago.com/pfc100/simulator")
    ai0 = client.get_node(ua.NodeId("AnalogInputs.AI0", idx))
    print(await ai0.read_value())
    do0 = client.get_node(ua.NodeId("DigitalOutputs.DO0", idx))
    await do0.write_value(True)
```

## Tests

```bash
python -m pytest
```

Les tests démarrent le serveur sur `127.0.0.1` (port aléatoire) et vérifient la lecture, l'écriture, le refus d'écriture en lecture seule, la simulation animée, la structure des dossiers et la validation du JSON.

## Structure du projet

```
main.py                     point d'entrée CLI
config/points.json          exemple de liste de points (style Wago PFC100)
examples/client_example.py  client de démonstration
src/opc_simulator/
  models.py                 dataclasses + table des types OPC UA
  config_loader.py          chargement et validation du JSON
  simulation.py             moteur d'animation des valeurs
  server.py                 construction de l'address space et serveur
tests/test_simulator.py     tests d'intégration (loopback)
```
