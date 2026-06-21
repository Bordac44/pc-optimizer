# PC Optimizer Pro

> Outil d'optimisation et de surveillance pour PC de jeu sous Windows, en Python / tkinter.

![Version](https://img.shields.io/badge/version-3.4-19d6f5)
![Plateforme](https://img.shields.io/badge/plateforme-Windows-blue)
![Python](https://img.shields.io/badge/python-3.14-yellow)

<!-- [À COMPLÉTER] Ajoute ici une capture d'écran du Dashboard : -->
<!-- ![Aperçu](docs/screenshots/dashboard.png) -->

## Présentation

PC Optimizer Pro regroupe la surveillance système en temps réel et un large
ensemble d'outils d'optimisation, de nettoyage et de configuration de Windows
dans une interface unique à onglets. L'application embarque **72 actions
documentées**, chacune décrite directement dans l'onglet « Aide ».

L'exécutable est **autonome** : aucune installation de Python ni de
bibliothèque externe n'est nécessaire pour l'utilisateur final.

> ⚠️ **Privilèges administrateur requis.** L'application s'exécute en tant
> qu'administrateur (badge « ADMINISTRATEUR » visible en haut de la fenêtre) car
> la plupart des actions touchent au registre, aux services et au système.

> 🛟 **Sécurité.** Un bouton « Créer un point de restauration » permet de revenir
> à l'état actuel en cas de problème, et l'onglet Rapport propose une sauvegarde /
> restauration des valeurs de registre et services modifiés par l'application.

## Surveillance en temps réel (Dashboard)

Le Dashboard affiche quatre jauges d'utilisation :

| Jauge | Source |
|---|---|
| 🖥️ Processeur (CPU) | `psutil` |
| 🎮 Carte graphique (GPU) | Compteurs de performance Windows |
| 🧠 Mémoire (RAM) | `psutil` |
| 💾 Disque C: | `psutil` |

Le pourcentage **GPU** est lu via le compteur Windows
`\GPU Engine(*)\Utilization Percentage` — la même source que l'onglet
« Performances » du Gestionnaire des tâches. Cette méthode est **universelle**
(NVIDIA, AMD, Intel) et ne nécessite **aucune dépendance ni DLL externe**.
C'est une agrégation des moteurs graphiques, pas une lecture matérielle brute.
Fonctionne sur Windows 10 (build 1709+) et Windows 11.

Le Dashboard inclut également un graphique d'utilisation CPU sur 60 secondes et
un récapitulatif des informations système.

## Onglets

### 📊 Dashboard
Jauges temps réel (CPU, GPU, RAM, Disque), graphique CPU, infos système.

### 🎮 Optimisation
Le cœur de l'application, organisé en quatre sections :

- **Réparation système** : SFC /scannow, DISM RestoreHealth, planification d'un
  ChkDsk sur C:, vérification de l'intégrité du registre.
- **Mises à jour** : tout mettre à jour via Winget, pilotes via Windows Update,
  raccourcis vers les pilotes NVIDIA (NVIDIA App) et AMD (Adrenalin), détection
  automatique du GPU, installation des runtimes Visual C++ / .NET.
- **Optimisation gaming** : plans d'alimentation Haute Performance et Ultimate
  Performance, Game Mode, HAGS (planification GPU matérielle), désactivation de
  l'accélération souris, de l'algorithme Nagle, de la Xbox Game Bar, de la
  capture/DVR et des animations Windows, priorité CPU/GPU pour les jeux, timer
  système haute résolution, priorité multimédia (réglages avancés du registre).
- **Mémoire & services** : libération de la mémoire des processus inactifs,
  désactivation de la compression mémoire, Large System Cache, SysMain, Windows
  Search, hibernation, Error Reporting, et optimisation du démarrage (boot).

Un bouton **« Choisir les optimisations à lancer »** ouvre une fenêtre où l'on
coche les optimisations à appliquer (toutes cochées par défaut), avec création
optionnelle d'un point de restauration avant exécution.

### 🧹 Nettoyage
Vider les fichiers temporaires, la Corbeille, le cache DNS, le cache du Windows
Store, le cache des miniatures, Prefetch, les composants anciens et les journaux
d'événements ; optimisation du disque C: (TRIM sur SSD, défragmentation sur HDD) ;
nettoyage Windows (cleanmgr). Un bouton **« TOUT NETTOYER »** enchaîne les
nettoyages en séquence.

### 🌐 Réseau
- **Test de connexion** : test de ping (latence) vers 1.1.1.1, affichage des
  informations IP détaillées.
- **Configuration réseau** : bascule des DNS (Cloudflare, Google ou automatique),
  désactivation de l'auto-tuning TCP, optimisation TCP/IP (QoS), désactivation
  d'IPv6, optimisation de l'adaptateur réseau, réinitialisation complète de la
  pile réseau.

### 🔥 Processus
Liste des processus les plus gourmands (PID, nom, % CPU, mémoire en Mo), avec
possibilité de terminer un processus sélectionné et de rafraîchir la liste.

### 🚀 Démarrage
Liste des programmes lancés au démarrage de Windows (programme, source de la clé
de registre HKCU/HKLM, chemin/commande), avec possibilité de retirer un programme
du démarrage (il reste installé).

### 🔒 Confidentialité
Désactivation de la télémétrie Windows, de Cortana, des publicités Windows, de
l'historique d'activité, de la localisation, des diagnostics & feedback, des
suggestions du menu Démarrer et de l'identifiant publicitaire. Un bouton applique
les réglages de confidentialité recommandés en une fois.

### 📈 Historique
Graphique d'utilisation CPU / Mémoire / Disque sur une période allant jusqu'à 24h.

### 📄 Rapport
Génération d'un rapport HTML complet de la configuration (matériel, disques,
réseau), ouverture du fichier journal (.log), vérification des mises à jour, et
sauvegarde / restauration des réglages (valeurs de registre et services modifiés
par l'application).

### ❓ Aide
Liste de recherche des 72 actions de l'application, chacune accompagnée d'une
description. Les info-bulles s'affichent aussi au survol de n'importe quel bouton.

## Fonctions globales

Boutons présents en haut de la fenêtre : **Arrêter** et **Redémarrer**
l'ordinateur (avec confirmation et délai de 5 s), et **Paramètres**. L'application
dispose d'une icône dans la barre des tâches (system tray) avec notifications
Windows, et d'une vérification automatique des mises à jour via les Releases
GitHub.

## Installation (utilisateur final)

1. Va dans la section [Releases](../../releases) du dépôt.
2. Télécharge le fichier `PCOptimizerPro.exe` de la dernière version.
3. Lance-le (clic droit → « Exécuter en tant qu'administrateur » si nécessaire).

Aucune installation de Python n'est nécessaire : l'exécutable est autonome.

## Compilation depuis les sources (développeur)

Prérequis : Windows et Python 3.14.

```powershell
# 1. Installer les dépendances
pip install -r requirements.txt
pip install pyinstaller

# 2. Compiler à partir du fichier .spec fourni
pyinstaller PCOptimizerPro.spec
```

L'exécutable autonome est généré dans le dossier `dist/`.

## Dépendances

- [psutil](https://pypi.org/project/psutil/) — métriques système (CPU, RAM, disque, processus)
- [pystray](https://pypi.org/project/pystray/) — icône dans la barre des tâches
- [Pillow](https://pypi.org/project/Pillow/) — images / icônes

La surveillance GPU n'utilise aucune bibliothèque tierce : elle repose
uniquement sur PowerShell et les compteurs de performance intégrés à Windows.

## Avertissement

Cet outil applique des modifications système (registre, services, réseau,
nettoyage de fichiers). Certaines actions sont signalées « ATTENTION » ou
« AVANCÉ » dans l'application. Il est recommandé de créer un point de
restauration avant toute modification importante. Utilisation à vos propres
risques.
