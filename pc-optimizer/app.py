import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import ctypes
import sys
import os
import platform
import time
import datetime
import urllib.request
import json
import tempfile
import base64

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


# === DROITS ADMINISTRATEUR ===
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()


# === PALETTE ===
# Couleurs mesurées sur le visuel du site (image fournie par l'utilisateur) :
# fond bleu nuit turquoise très sombre (#00142b–#011f40), accent cyan (#06e0fb).
BG      = "#00142b"   # fond principal — bleu nuit de l'image
BG2     = "#03203c"   # panneaux / en-tête
BG3     = "#0c2e4e"   # éléments en relief / survol / onglet actif
CARD    = "#07243f"   # cartes
ACCENT  = "#19d6f5"   # cyan (proche du glow #06e0fb de l'image)
ACCENT2 = "#ff6b35"
TEXT    = "#e6edf3"
MUTED   = "#8b949e"
SUCCESS = "#3fb950"
WARNING = "#d29922"
ERROR   = "#f85149"
PURPLE  = "#bc8cff"

# === CONFIGURATION MISE À JOUR ===
VERSION     = "3.4"
GITHUB_USER = "Bordac44"
GITHUB_REPO = "pc-optimizer"
API_URL     = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

# === DÉMARRAGE AUTOMATIQUE (clé de registre HKCU\...\Run) ===
STARTUP_RUN_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_RUN_NAME = "PCOptimizerPro"


def _version_tuple(v):
    """Convertit '3.10' en (3, 10) pour comparer correctement les versions."""
    try:
        return tuple(int(x) for x in str(v).lstrip("vV").strip().split("."))
    except:
        return (0,)


# === INFO-BULLES — descriptions affichées au survol et dans l'onglet Aide ===
ACTION_TIPS = {
    # Sécurité
    "✚  Créer un point de restauration":
        "Crée une sauvegarde Windows permettant de revenir à l'état actuel "
        "en cas de problème. À faire avant toute modification importante.",
    # Réparation système
    "SFC /scannow":
        "Analyse l'intégrité des fichiers système Windows et répare ceux "
        "qui sont corrompus. Sans risque. Durée : 5-15 minutes.",
    "DISM RestoreHealth":
        "Restaure les composants Windows endommagés en téléchargeant les "
        "versions saines depuis Windows Update. Nécessite Internet.",
    "ChkDsk — Planifier (C:)":
        "Programme une vérification approfondie du disque C: au prochain "
        "redémarrage. Corrige les erreurs du système de fichiers.",
    "Vérifier intégrité registre":
        "Vérifie l'image Windows sans la réparer. Plus rapide que DISM "
        "RestoreHealth.",
    # Mises à jour
    "Winget — Tout mettre à jour":
        "Met à jour tous les logiciels installés via le gestionnaire de "
        "paquets Windows (Chrome, VLC, Steam, Discord, etc.).",
    "Pilotes — Windows Update":
        "Cherche et installe les mises à jour de pilotes proposées par "
        "Microsoft via Windows Update.",
    "Pilotes NVIDIA (GeForce Exp.)":
        "Ouvre la page officielle NVIDIA App (qui remplace GeForce "
        "Experience) pour télécharger les derniers pilotes.",
    "Pilotes AMD (Adrenalin)":
        "Ouvre la page officielle AMD Adrenalin pour télécharger les "
        "derniers pilotes Radeon.",
    "Détecter mon GPU & installer":
        "Détecte automatiquement votre carte graphique (NVIDIA, AMD ou "
        "Intel) et propose le bon installeur de pilotes.",
    "Runtimes VC++ / .NET":
        "Installe les bibliothèques Visual C++ et .NET nécessaires à de "
        "nombreux logiciels et jeux récents.",
    # Gaming
    "Plan Haute Performance":
        "Active le plan d'alimentation « Performances élevées » de Windows. "
        "Maximise les performances au détriment de la consommation.",
    "Plan Ultimate Performance":
        "Plan « Performances ultimes » (Windows Pro/Workstation). Aucune "
        "limitation de fréquence — chauffe et consomme davantage.",
    "Activer Game Mode":
        "Active le mode jeu Windows : limite les notifications, réduit "
        "les processus en arrière-plan, priorise les ressources pour le "
        "jeu actif.",
    "Activer HAGS (GPU Scheduling)":
        "Active la planification GPU accélérée matériellement. Peut "
        "améliorer les performances et réduire la latence (GPU NVIDIA "
        "GTX 1000+ ou AMD Radeon 5000+). Redémarrage requis.",
    "Désactiver accélération souris":
        "Désactive l'accélération de la souris pour un mouvement 1:1 "
        "plus précis. Recommandé pour les FPS compétitifs.",
    "Désactiver Nagle — jeux en ligne (exp.)":
        "Désactive l'algorithme Nagle qui retarde l'envoi de petits "
        "paquets TCP. Peut réduire le ping en jeu. EXPÉRIMENTAL : peut "
        "perturber certaines applications réseau.",
    "Priorité CPU/GPU — Jeux":
        "Configure le système pour donner la priorité aux jeux dans la "
        "gestion CPU et GPU. Désactive le throttling réseau.",
    "Désactiver Xbox Game Bar":
        "Désactive la barre de jeu Xbox (Win+G). Libère de la mémoire et "
        "évite les conflits avec certains jeux.",
    "Désactiver capture/DVR":
        "Désactive l'enregistrement automatique des sessions de jeu. "
        "Libère du CPU/GPU pendant le jeu.",
    "Désactiver animations Windows":
        "Désactive les animations et effets visuels de Windows pour une "
        "interface plus réactive.",
    "Timer système — avancé (redémarrage)":
        "Force Windows à utiliser le timer matériel haute résolution. "
        "Effet variable selon la machine. Redémarrage requis. AVANCÉ.",
    "Priorité multimédia Windows (avancé)":
        "Modifie les paramètres registre de priorité multimédia pour "
        "favoriser les jeux. AVANCÉ : modifications profondes du registre.",
    # Mémoire & Services
    "Libérer mémoire processus inactifs":
        "Force le garbage collector à libérer la mémoire des processus "
        "inactifs. Note : ne vide PAS la standby list Windows réelle.",
    "Désactiver compression mémoire":
        "Désactive la compression mémoire de Windows. Peut améliorer les "
        "performances sur machines avec beaucoup de RAM (>16 Go).",
    "Activer Large System Cache":
        "Augmente le cache mémoire du noyau Windows. Convient aux "
        "machines avec beaucoup de RAM (>16 Go).",
    "Désactiver SysMain":
        "Désactive SysMain (anciennement Superfetch). Réduit l'activité "
        "disque mais peut ralentir le démarrage des apps fréquentes.",
    "Désactiver Windows Search":
        "Désactive l'indexation Windows. ATTENTION : la recherche dans "
        "l'explorateur sera beaucoup plus lente.",
    "Désactiver hibernation":
        "Désactive l'hibernation et supprime hiberfil.sys. Libère "
        "plusieurs Go d'espace disque.",
    "Désactiver Error Reporting":
        "Désactive l'envoi automatique des rapports d'erreurs à Microsoft.",
    "Optimiser le démarrage (boot)":
        "Optimise les paramètres de démarrage Windows : menu rapide, "
        "démarrage silencieux, timeout réduit à 5 secondes.",
    # Nettoyage
    "Vider les fichiers Temp":
        "Supprime tous les fichiers temporaires (profil utilisateur + "
        "Windows). Sans risque, peut libérer plusieurs Go.",
    "Vider la Corbeille":
        "Vide la Corbeille Windows. Les fichiers ne pourront plus être "
        "récupérés.",
    "Vider le cache DNS":
        "Vide le cache de résolution DNS. Utile en cas de problèmes "
        "d'accès à certains sites web.",
    "Optimiser le disque C:":
        "Lance l'optimisation du disque C: (TRIM sur SSD, défragmentation "
        "sur HDD).",
    "Nettoyer Prefetch":
        "Supprime les fichiers de pré-chargement Windows. Peut ralentir "
        "temporairement les premiers démarrages d'applications.",
    "Nettoyage Windows (cleanmgr)":
        "Lance Disk Cleanup de Windows en mode automatique pour nettoyer "
        "les fichiers obsolètes.",
    "Vider cache Windows Store":
        "Réinitialise le cache du Microsoft Store. Utile en cas de "
        "problèmes de téléchargement d'applications.",
    "Nettoyer composants anciens":
        "Supprime les anciennes versions des composants Windows. "
        "ATTENTION IRRÉVERSIBLE : après cette action, les mises à jour "
        "Windows déjà installées ne pourront plus être désinstallées.",
    "Nettoyer cache miniatures":
        "Vide le cache des miniatures de l'explorateur Windows. Les "
        "vignettes seront régénérées au prochain accès.",
    "Vider les logs d'événements":
        "Supprime tous les journaux d'événements Windows. ATTENTION : "
        "perte de tout l'historique de diagnostic du système.",
    # Réseau
    "🏓  Tester le ping (latence)":
        "Envoie 8 paquets ping vers 1.1.1.1 (Cloudflare) pour mesurer "
        "la latence réseau.",
    "🌍  Afficher mes infos IP":
        "Affiche les informations détaillées de configuration réseau "
        "(IP, masque, passerelle, DNS).",
    "DNS → Cloudflare (1.1.1.1)":
        "Configure les DNS Cloudflare 1.1.1.1 et 1.0.0.1. Très rapides "
        "et respectueux de la vie privée.",
    "DNS → Google (8.8.8.8)":
        "Configure les DNS Google 8.8.8.8 et 8.8.4.4. Rapides et fiables.",
    "DNS → Automatique (défaut)":
        "Restaure les DNS automatiques fournis par votre fournisseur "
        "d'accès Internet.",
    "Désactiver auto-tuning TCP":
        "Désactive l'ajustement automatique de la fenêtre TCP. Peut "
        "résoudre certains problèmes de débit.",
    "Optimiser TCP/IP (QoS)":
        "Désactive ECN et active DCA pour améliorer les performances "
        "réseau sur connexions modernes.",
    "Désactiver IPv6":
        "Désactive IPv6 sur tous les adaptateurs. ATTENTION : peut "
        "casser certains VPN ou services modernes.",
    "Optimiser adaptateur réseau":
        "Désactive l'Interrupt Moderation pour une latence réseau plus "
        "faible. Recommandé pour le gaming en ligne.",
    "Réinitialiser la pile réseau":
        "Réinitialise complètement la pile réseau Windows (TCP/IP, "
        "Winsock). Résout la plupart des problèmes réseau persistants.",
    # Confidentialité
    "Désactiver télémétrie Windows":
        "Désactive l'envoi de données d'usage à Microsoft. Réduit le "
        "trafic réseau en arrière-plan.",
    "Désactiver Cortana":
        "Désactive l'assistant Cortana. Libère de la mémoire et arrête "
        "sa collecte de données.",
    "Désactiver publicités Windows":
        "Désactive les publicités dans le menu Démarrer, l'explorateur "
        "et l'écran de verrouillage.",
    "Désactiver Activity History":
        "Désactive l'historique d'activité partagé entre vos appareils "
        "Microsoft.",
    "Désactiver localisation":
        "Désactive complètement les services de localisation Windows.",
    "Désactiver diagnostics & feedback":
        "Désactive l'envoi de diagnostics et les demandes de feedback "
        "de Microsoft.",
    "Désactiver suggestions démarrage":
        "Désactive les suggestions d'applications dans le menu Démarrer.",
    "Désactiver l'ID de publicité":
        "Désactive l'identifiant publicitaire unique de Windows utilisé "
        "pour le ciblage publicitaire.",
    # Boutons globaux
    "⚙️  Choisir les optimisations à lancer":
        "Ouvre une fenêtre où vous cochez les optimisations à appliquer "
        "(tout est coché par défaut). Un point de restauration peut être "
        "créé avant de lancer.",
    "🧹   TOUT NETTOYER":
        "Lance tous les nettoyages en séquence : Temp, Prefetch, "
        "miniatures, DNS, Corbeille, disque.",
    "🔒   Appliquer les réglages confidentialité recommandés":
        "Applique tous les réglages de confidentialité : télémétrie, "
        "Cortana, publicités, ID publicitaire.",
    "📊  Générer le rapport HTML":
        "Génère un rapport HTML détaillé de la configuration matérielle "
        "et système. Enregistré sur le Bureau.",
    "📁  Ouvrir le fichier journal (.log)":
        "Ouvre le journal des actions effectuées dans votre éditeur de "
        "texte par défaut.",
    "🔍  Vérifier les mises à jour":
        "Vérifie si une nouvelle version de PC Optimizer Pro est "
        "disponible sur GitHub.",
    "⟳ Redémarrer":
        "Redémarre l'ordinateur (avec confirmation et délai de 5 sec).",
    "⏻ Arrêter":
        "Éteint l'ordinateur (avec confirmation et délai de 5 sec).",
    "⛔  Terminer le processus":
        "Termine le processus sélectionné dans la liste. Attention aux "
        "processus système critiques.",
    "⛔  Retirer du démarrage":
        "Empêche le programme sélectionné de se lancer automatiquement "
        "avec Windows. Le programme reste installé.",
    "🔄  Rafraîchir":
        "Recharge la liste actuelle.",
    "💾  Créer une sauvegarde (registre/services)":
        "Sauvegarde l'état actuel des valeurs de registre et des services "
        "modifiés par l'application, dans un dossier « backups ». Permet de "
        "revenir en arrière via la restauration.",
    "↩️  Restaurer la dernière sauvegarde":
        "Réapplique l'état enregistré lors de la dernière sauvegarde "
        "(registre, services, plan d'alimentation). Un redémarrage peut "
        "être nécessaire.",
}


# === VALEURS DE REGISTRE SAUVEGARDÉES / RESTAURÉES (tweaks de l'app) ===
# Chaque entrée : (ruche "HKCU"/"HKLM", sous-clé, nom de la valeur).
# La sauvegarde lit l'état actuel ; la restauration remet la valeur d'origine
# (ou la supprime si elle n'existait pas avant). Couvre les tweaks registre +
# le type de démarrage des services (valeur "Start"). Ne couvre PAS : Nagle
# (clés par interface, dynamiques), suppressions de fichiers, ResetBase,
# réinitialisation réseau, compression mémoire (MMAgent).
REG_BACKUP = [
    # Gaming
    ("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled"),
    ("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode"),
    ("HKCU", r"Software\Microsoft\GameBar", "UseNexusForGameBarEnabled"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode"),
    ("HKCU", r"Control Panel\Mouse", "MouseSpeed"),
    ("HKCU", r"Control Panel\Mouse", "MouseThreshold1"),
    ("HKCU", r"Control Panel\Mouse", "MouseThreshold2"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
     "SystemResponsiveness"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
     "Priority"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
     "Scheduling Category"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
     "GPU Priority"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
     "Clock Rate"),
    ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled"),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
     "VisualFXSetting"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
     "LargeSystemCache"),
    # Confidentialité
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry"),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "AllowCortana"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338389Enabled"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SystemPaneSuggestionsEnabled"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338393Enabled"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-353694Enabled"),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
     "Value"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy",
     "TailoredExperiencesWithDiagnosticDataEnabled"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled"),
    # Services (valeur "Start" : 2=Auto, 3=Manuel, 4=Désactivé)
    ("HKLM", r"SYSTEM\CurrentControlSet\Services\SysMain", "Start"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Services\DiagTrack", "Start"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Services\dmwappushservice", "Start"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Services\WSearch", "Start"),
    ("HKLM", r"SYSTEM\CurrentControlSet\Services\WerSvc", "Start"),
]


class Tooltip:
    """Info-bulle qui apparaît au survol d'un widget après un court délai."""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event=None):
        self._cancel()
        self.after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except:
                pass
            self.after_id = None

    def _show(self):
        if self.tooltip_window or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tooltip_window = tk.Toplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tooltip_window, text=self.text,
                     justify=tk.LEFT, background=CARD,
                     foreground=TEXT, relief=tk.SOLID, borderwidth=1,
                     font=("Segoe UI", 9), wraplength=380,
                     padx=10, pady=6).pack()
        except:
            self.tooltip_window = None

    def _hide(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None


class GPUMonitor:
    """Lecture du pourcentage d'utilisation GPU via les compteurs de
    performance de Windows (« \\GPU Engine(*)\\Utilization Percentage »).

    Universel : fonctionne pour les cartes NVIDIA, AMD et Intel sur
    Windows 10 (build 1709 et ultérieures) et Windows 11, sans aucune
    dépendance Python ni DLL externe. La valeur renvoyée est une agrégation
    des moteurs graphiques, cohérente avec l'onglet « Performances » du
    Gestionnaire des tâches de Windows.

    Tout est appelé paresseusement depuis le thread de monitoring : si le
    compteur est absent (matériel/OS trop ancien), on bascule simplement en
    mode indisponible (available=False) sans planter l'application.
    """

    # Script PowerShell : agrège l'utilisation par type de moteur graphique
    # (3D, Copy, VideoDecode, ...), prend le maximum, et renvoie un entier
    # 0-100. Renvoie « NA » si le compteur n'est pas disponible.
    _PS = (
        "$ErrorActionPreference='Stop';"
        "try{"
        "$s=(Get-Counter '\\GPU Engine(*)\\Utilization Percentage').CounterSamples;"
        "$g=$s|Group-Object {($_.InstanceName -split 'engtype_')[-1]}|"
        "ForEach-Object {($_.Group|Measure-Object CookedValue -Sum).Sum};"
        "$m=($g|Measure-Object -Maximum).Maximum;"
        "if($m -gt 100){$m=100};"
        "[int][math]::Round($m)"
        "}catch{'NA'}"
    )

    def __init__(self):
        self.available = None     # None = pas encore testé
        self.error = ""

    def read_percent(self):
        """Renvoie le % d'utilisation GPU (float 0-100) ou None si indispo."""
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-Command", self._PS],
                text=True, encoding="utf-8", errors="replace", timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip()
            if not out or out.upper().startswith("NA"):
                self.available = False
                if not self.error:
                    self.error = "Compteur GPU indisponible"
                return None
            val = float(out)
            self.available = True
            return max(0.0, min(100.0, val))
        except Exception as e:
            self.available = False
            self.error = str(e)
            return None

    def close(self):
        pass


class PCOptimizerPro:
    def __init__(self, root):
        self.root = root
        self.root.title(f"PC Optimizer Pro v{VERSION}")
        self.root.geometry("1200x800")
        self.root.configure(bg=BG)
        self.root.minsize(1000, 700)

        self.monitoring = True
        self.cpu_history = [0] * 60

        self.tray_icon = None
        self.last_alert_level = "ok"
        self.last_alert_time = 0
        self.history = []
        self._last_history_save = 0
        self._restore_point_offered = False
        self.gpu_monitor = GPUMonitor()
        self._last_gpu = 0        # dernier % GPU connu (lu toutes les ~2 s)
        self._gpu_tick = 0
        self.setup_logging()
        self.load_settings()
        self._load_history()
        self.setup_style()
        self.build_ui()
        self.load_sysinfo()
        self.start_monitor()
        if HAS_TRAY:
            self._setup_tray()
            # Démarre minimisé uniquement si l'utilisateur l'a choisi
            if self.settings.get("start_minimized", False):
                self.root.after(200, self._start_minimized)
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        # Le bouton « réduire » peut envoyer l'appli au tray (si activé)
        self.root.bind("<Unmap>", self._on_minimize_event)
        # Vérification des mises à jour au démarrage (si activé)
        if self.settings.get("check_updates_on_start", False):
            self.root.after(3000, lambda: self.check_update(silent=True))

    # ================================================================== #
    #  JOURNAL                                                             #
    # ================================================================== #
    def setup_logging(self):
        try:
            base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
                   else os.path.dirname(os.path.abspath(__file__))
            self.log_path = os.path.join(base, "pcoptimizer.log")
        except:
            self.log_path = "pcoptimizer.log"

    def write_log(self, text):
        try:
            stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {text}\n")
        except:
            pass

    # ================================================================== #
    #  RÉGLAGES (préférences utilisateur)                                  #
    # ================================================================== #
    def _base_dir(self):
        return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
               else os.path.dirname(os.path.abspath(__file__))

    def _settings_path(self):
        return os.path.join(self._base_dir(), "settings.json")

    def _default_settings(self):
        # Par défaut : fenêtre normale au lancement, fermeture = réduction au tray.
        return {"start_minimized": False, "close_to_tray": True,
                "check_updates_on_start": False, "minimize_to_tray": False}

    def load_settings(self):
        """Charge les préférences depuis settings.json (avec valeurs par défaut)."""
        self.settings = self._default_settings()
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in self.settings:
                    if k in data:
                        self.settings[k] = bool(data[k])
        except Exception:
            pass  # fichier absent au premier lancement = valeurs par défaut

    def save_settings(self):
        """Écrit les préférences sur disque."""
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.write_log(f"Échec sauvegarde settings : {e}")

    # --- Démarrage avec Windows (clé de registre) -----------------------
    def _startup_command(self):
        """Commande à enregistrer pour lancer l'appli au démarrage."""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        # Mode script (développement) : python + chemin du script
        script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] \
                 else os.path.abspath(__file__)
        return f'"{sys.executable}" "{script}"'

    def _is_startup_enabled(self):
        """True si la clé de démarrage automatique existe."""
        if not HAS_WINREG:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY,
                                0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, STARTUP_RUN_NAME)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _set_startup_enabled(self, enabled):
        """Ajoute ou retire la clé de démarrage automatique. Retourne True si OK."""
        if not HAS_WINREG:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY,
                                0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, STARTUP_RUN_NAME, 0,
                                      winreg.REG_SZ, self._startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, STARTUP_RUN_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            self.write_log(f"Échec écriture clé démarrage : {e}")
            return False

    # ================================================================== #
    #  STYLE                                                               #
    # ================================================================== #
    def setup_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG2, foreground=MUTED,
                    padding=[18, 10], font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", BG3)],
              foreground=[("selected", ACCENT)])
        s.configure("Treeview", background=CARD, foreground=TEXT,
                    fieldbackground=CARD, borderwidth=0, rowheight=24)
        s.configure("Treeview.Heading", background=BG3, foreground=ACCENT,
                    font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", BG)])
        s.configure("Vertical.TScrollbar", background=BG3, troughcolor=BG,
                    borderwidth=0, arrowcolor=ACCENT)

    # ================================================================== #
    #  CONSTRUCTION UI                                                     #
    # ================================================================== #
    def build_ui(self):
        # --- En-tête ---
        hdr = tk.Frame(self.root, bg=BG2, height=62)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡ PC OPTIMIZER", font=("Segoe UI", 18, "bold"),
                 bg=BG2, fg=ACCENT).pack(side=tk.LEFT, padx=20, pady=12)
        tk.Label(hdr, text=f"PRO v{VERSION}", font=("Segoe UI", 9),
                 bg=BG2, fg=ACCENT2).pack(side=tk.LEFT, pady=12)
        tk.Button(hdr, text="⚙️ Paramètres", command=self.open_settings,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=4, pady=14)
        tk.Button(hdr, text="⟳ Redémarrer", command=self.reboot_pc,
                  font=("Segoe UI", 8), bg=BG3, fg=WARNING, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=4, pady=14)
        tk.Button(hdr, text="⏻ Arrêter", command=self.shutdown_pc,
                  font=("Segoe UI", 8), bg=BG3, fg=ERROR, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=4, pady=14)
        tk.Label(hdr, text="✓ ADMINISTRATEUR", font=("Segoe UI", 8, "bold"),
                 bg=BG2, fg=SUCCESS).pack(side=tk.RIGHT, padx=20)
        if not HAS_PSUTIL:
            tk.Label(hdr, text="⚠ psutil manquant — monitoring limité",
                     font=("Segoe UI", 8), bg=BG2, fg=WARNING).pack(side=tk.RIGHT, padx=10)
        self.root.bind("<F5>", lambda e: self._refresh_active())

        # --- Onglets ---
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        self.tab_dash    = tk.Frame(self.nb, bg=BG)
        self.tab_opt     = tk.Frame(self.nb, bg=BG)
        self.tab_clean   = tk.Frame(self.nb, bg=BG)
        self.tab_net     = tk.Frame(self.nb, bg=BG)
        self.tab_proc    = tk.Frame(self.nb, bg=BG)
        self.tab_startup = tk.Frame(self.nb, bg=BG)
        self.tab_priv    = tk.Frame(self.nb, bg=BG)
        self.tab_history = tk.Frame(self.nb, bg=BG)
        self.tab_report  = tk.Frame(self.nb, bg=BG)
        self.tab_help    = tk.Frame(self.nb, bg=BG)

        self.nb.add(self.tab_dash,    text="  📊  Dashboard  ")
        self.nb.add(self.tab_opt,     text="  🎮  Optimisation  ")
        self.nb.add(self.tab_clean,   text="  🧹  Nettoyage  ")
        self.nb.add(self.tab_net,     text="  🌐  Réseau  ")
        self.nb.add(self.tab_proc,    text="  🔥  Processus  ")
        self.nb.add(self.tab_startup, text="  🚀  Démarrage  ")
        self.nb.add(self.tab_priv,    text="  🔒  Confidentialité  ")
        self.nb.add(self.tab_history, text="  📈  Historique  ")
        self.nb.add(self.tab_report,  text="  📄  Rapport  ")
        self.nb.add(self.tab_help,    text="  ❓  Aide  ")

        self.build_dashboard()
        self.build_optimize()
        self.build_cleanup()
        self.build_network()
        self.build_processes()
        self.build_startup()
        self.build_privacy()
        self.build_history()
        self.build_report()
        self.build_help()

        # --- Console partagée (CORRECTION : placée ici, plus dans _refresh_active) ---
        cframe = tk.Frame(self.root, bg=BG)
        cframe.pack(fill=tk.X, padx=8, pady=(0, 4))
        ctop = tk.Frame(cframe, bg=BG)
        ctop.pack(fill=tk.X)
        tk.Label(ctop, text="📋  Console", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=TEXT).pack(side=tk.LEFT)
        tk.Button(ctop, text="Enregistrer", command=self.save_console,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=4)
        tk.Button(ctop, text="Copier", command=self.copy_console,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=4)
        tk.Button(ctop, text="Effacer", command=self.clear_console,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT)
        self.console = scrolledtext.ScrolledText(
            cframe, bg="#05080f", fg=SUCCESS, font=("Consolas", 9),
            relief=tk.FLAT, height=8, insertbackground="white", state=tk.DISABLED)
        self.console.pack(fill=tk.X, pady=(4, 0))

        # --- Barre de statut ---
        self.status_var = tk.StringVar(value="✓  Prêt")
        tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 9),
                 bg=BG2, fg=SUCCESS, anchor=tk.W, padx=12, pady=4
                 ).pack(fill=tk.X)

        # Attache les info-bulles à tous les boutons reconnus (texte == clé ACTION_TIPS)
        self._attach_all_tips()

    def _refresh_active(self):
        """CORRECTION : ne contient plus la création de la console."""
        try:
            tab = self.nb.index(self.nb.select())
        except:
            return
        if tab == 4:
            self.refresh_processes()
        elif tab == 5:
            self.refresh_startup()
        self.set_status("✓  Actualisé (F5)")

    def _attach_all_tips(self):
        """Parcourt récursivement tous les widgets et attache une info-bulle
        à chaque bouton dont le texte correspond exactement à une clé d'ACTION_TIPS."""
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Button):
                    try:
                        label = child.cget("text")
                    except Exception:
                        label = ""
                    if label in ACTION_TIPS:
                        Tooltip(child, ACTION_TIPS[label])
                walk(child)
        try:
            walk(self.root)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  ONGLET DASHBOARD                                                    #
    # ------------------------------------------------------------------ #
    def build_dashboard(self):
        p = self.tab_dash
        gauges = tk.Frame(p, bg=BG)
        gauges.pack(fill=tk.X, padx=20, pady=20)

        self.gauge_canvas = {}
        self.gauge_text = {}
        for i, (key, label, color) in enumerate([
            ("cpu",  "PROCESSEUR",      ACCENT),
            ("gpu",  "CARTE GRAPHIQUE", ACCENT2),
            ("ram",  "MÉMOIRE",         PURPLE),
            ("disk", "DISQUE C:",       SUCCESS)]):
            card = tk.Frame(gauges, bg=CARD, width=210, height=200)
            card.grid(row=0, column=i, padx=8, sticky=tk.NSEW)
            card.pack_propagate(False)
            gauges.grid_columnconfigure(i, weight=1)

            cv = tk.Canvas(card, width=170, height=140, bg=CARD, highlightthickness=0)
            cv.pack(pady=(14, 0))
            self.gauge_canvas[key] = (cv, color)
            txt = tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                           bg=CARD, fg=MUTED)
            txt.pack()
            self.gauge_text[key] = txt

        graph_card = tk.Frame(p, bg=CARD)
        graph_card.pack(fill=tk.X, padx=20, pady=(0, 14))
        tk.Label(graph_card, text="📈  Utilisation CPU (60 dernières secondes)",
                 font=("Segoe UI", 9, "bold"), bg=CARD, fg=ACCENT
                 ).pack(anchor=tk.W, padx=14, pady=(10, 0))
        self.graph = tk.Canvas(graph_card, height=120, bg="#05080f",
                               highlightthickness=0)
        self.graph.pack(fill=tk.X, padx=14, pady=12)

        info_card = tk.Frame(p, bg=CARD)
        info_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        tk.Label(info_card, text="💻  Informations système",
                 font=("Segoe UI", 9, "bold"), bg=CARD, fg=ACCENT
                 ).pack(anchor=tk.W, padx=14, pady=(10, 6))
        self.info_grid = tk.Frame(info_card, bg=CARD)
        self.info_grid.pack(fill=tk.X, padx=14, pady=(0, 12))
        self.info_labels = {}
        keys = ["Système", "Processeur", "Mémoire totale", "Carte graphique",
                "Disque C:", "Nom du PC", "Démarré depuis", "Utilisateur"]
        for i, k in enumerate(keys):
            r, c = i % 4, (i // 4) * 2
            tk.Label(self.info_grid, text=f"{k} :", font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=ACCENT2, anchor=tk.W, width=16
                     ).grid(row=r, column=c, sticky=tk.W, pady=3)
            lbl = tk.Label(self.info_grid, text="…", font=("Segoe UI", 8),
                           bg=CARD, fg=TEXT, anchor=tk.W)
            lbl.grid(row=r, column=c+1, sticky=tk.W, padx=(0, 30), pady=3)
            self.info_labels[k] = lbl

    def draw_gauge(self, key, value):
        cv, color = self.gauge_canvas[key]
        cv.delete("all")
        cx, cy, r = 85, 80, 58
        cv.create_arc(cx-r, cy-r, cx+r, cy+r, start=135, extent=-270,
                      style=tk.ARC, outline=BG3, width=12)
        col = SUCCESS if value < 60 else (WARNING if value < 85 else ERROR)
        extent = -270 * (value / 100)
        cv.create_arc(cx-r, cy-r, cx+r, cy+r, start=135, extent=extent,
                      style=tk.ARC, outline=col, width=12)
        cv.create_text(cx, cy-6, text=f"{int(value)}%",
                       font=("Segoe UI", 22, "bold"), fill=TEXT)
        cv.create_text(cx, cy+20, text="utilisé", font=("Segoe UI", 8), fill=MUTED)

    def draw_graph(self):
        self.graph.delete("all")
        w = self.graph.winfo_width() or 1000
        h = 120
        n = len(self.cpu_history)
        if n < 2:
            return
        step = w / (n - 1)
        for gy in (0.25, 0.5, 0.75):
            y = h * gy
            self.graph.create_line(0, y, w, y, fill=BG3, dash=(2, 4))
        pts = []
        for i, v in enumerate(self.cpu_history):
            x = i * step
            y = h - (v / 100 * h)
            pts.extend([x, y])
        if len(pts) >= 4:
            self.graph.create_line(*pts, fill=ACCENT, width=2, smooth=True)
            fill_pts = pts + [w, h, 0, h]
            self.graph.create_polygon(*fill_pts, fill=ACCENT, stipple="gray12",
                                      outline="")

    # ------------------------------------------------------------------ #
    #  HELPERS UI                                                          #
    # ------------------------------------------------------------------ #
    def make_scroll(self, parent):
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"

        def _bind_children(w):
            w.bind("<MouseWheel>", _wheel)
            for c in w.winfo_children():
                _bind_children(c)

        canvas.bind("<MouseWheel>", _wheel)
        frame.after(400, lambda: _bind_children(frame))
        return frame

    def card_section(self, parent, title, color=ACCENT):
        card = tk.Frame(parent, bg=CARD)
        card.pack(fill=tk.X, padx=16, pady=8)
        tk.Label(card, text=title, font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=color).pack(anchor=tk.W, padx=14, pady=(10, 2))
        tk.Frame(card, bg=color, height=2).pack(fill=tk.X, padx=14, pady=(0, 8))
        grid = tk.Frame(card, bg=CARD)
        grid.pack(fill=tk.X, padx=14, pady=(0, 12))
        return grid

    def grid_btn(self, parent, idx, text, cmd, color=None):
        b = tk.Button(parent, text=text, command=cmd,
                      font=("Segoe UI", 9), bg=BG3, fg=color or TEXT,
                      activebackground=ACCENT, activeforeground=BG,
                      relief=tk.FLAT, cursor="hand2", pady=9, padx=10,
                      anchor=tk.W, width=30)
        b.grid(row=idx // 2, column=idx % 2, padx=5, pady=4, sticky=tk.EW)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ #
    #  ONGLET OPTIMISATION (CORRECTION : sections remises en ordre)        #
    # ------------------------------------------------------------------ #
    def build_optimize(self):
        f = self.make_scroll(self.tab_opt)

        g = self.card_section(f, "🛡️  SÉCURITÉ", SUCCESS)
        self.grid_btn(g, 0, "✚  Créer un point de restauration",
                      self.run_restore_point, SUCCESS)

        g = self.card_section(f, "🔧  RÉPARATION SYSTÈME")
        for i, (t, c) in enumerate([
            ("SFC /scannow", self.run_sfc),
            ("DISM RestoreHealth", self.run_dism),
            ("ChkDsk — Planifier (C:)", self.run_chkdsk),
            ("Vérifier intégrité registre", self.run_registry_repair)]):
            self.grid_btn(g, i, t, c)

        g = self.card_section(f, "🔄  MISES À JOUR")
        for i, (t, c) in enumerate([
            ("Winget — Tout mettre à jour", self.run_winget),
            ("Pilotes — Windows Update", self.run_drivers_wu),
            ("Pilotes NVIDIA (GeForce Exp.)", self.run_nvidia),
            ("Pilotes AMD (Adrenalin)", self.run_amd),
            ("Détecter mon GPU & installer", self.run_detect_gpu),
            ("Runtimes VC++ / .NET", self.run_runtimes)]):
            self.grid_btn(g, i, t, c)

        g = self.card_section(f, "🎮  OPTIMISATION GAMING")
        for i, (t, c) in enumerate([
            ("Plan Haute Performance", self.run_power_plan),
            ("Plan Ultimate Performance", self.run_ultimate_power),
            ("Activer Game Mode", self.run_game_mode),
            ("Activer HAGS (GPU Scheduling)", self.run_hags),
            ("Désactiver accélération souris", self.run_mouse),
            ("Désactiver Nagle — jeux en ligne (exp.)", self.run_nagle),
            ("Priorité CPU/GPU — Jeux", self.run_priority),
            ("Désactiver Xbox Game Bar", self.run_gamebar),
            ("Désactiver capture/DVR", self.run_dvr),
            ("Désactiver animations Windows", self.run_animations),
            ("Timer système — avancé (redémarrage)", self.run_timer),
            ("Priorité multimédia Windows (avancé)", self.run_registry_gaming)]):
            self.grid_btn(g, i, t, c)

        g = self.card_section(f, "🧠  MÉMOIRE & SERVICES")
        for i, (t, c) in enumerate([
            ("Libérer mémoire processus inactifs", self.run_clear_standby),
            ("Désactiver compression mémoire", self.run_mem_compression),
            ("Activer Large System Cache", self.run_large_cache),
            ("Désactiver SysMain", self.run_sysmain),
            ("Désactiver Windows Search", self.run_wsearch),
            ("Désactiver hibernation", self.run_hibernation),
            ("Désactiver Error Reporting", self.run_wer),
            ("Optimiser le démarrage (boot)", self.run_boot_opt)]):
            self.grid_btn(g, i, t, c)

        big = tk.Frame(f, bg=BG)
        big.pack(fill=tk.X, padx=16, pady=14)
        tk.Button(big, text="⚙️  Choisir les optimisations à lancer",
                  command=self.run_all, font=("Segoe UI", 11, "bold"),
                  bg=ACCENT2, fg="white", activebackground="#ff8855",
                  relief=tk.FLAT, cursor="hand2", pady=13
                  ).pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    #  ONGLET NETTOYAGE                                                    #
    # ------------------------------------------------------------------ #
    def build_cleanup(self):
        f = self.make_scroll(self.tab_clean)
        g = self.card_section(f, "🧹  NETTOYAGE DU SYSTÈME")
        for i, (t, c) in enumerate([
            ("Vider les fichiers Temp", self.run_clean_temp),
            ("Vider la Corbeille", self.run_clean_bin),
            ("Vider le cache DNS", self.run_dns),
            ("Optimiser le disque C:", self.run_disk_opt),
            ("Nettoyer Prefetch", self.run_prefetch),
            ("Nettoyage Windows (cleanmgr)", self.run_cleanmgr),
            ("Vider cache Windows Store", self.run_store_cache),
            ("Nettoyer composants anciens", self.run_clean_winsxs),
            ("Nettoyer cache miniatures", self.run_thumb_cache),
            ("Vider les logs d'événements", self.run_event_logs)]):
            self.grid_btn(g, i, t, c)

        big = tk.Frame(f, bg=BG)
        big.pack(fill=tk.X, padx=16, pady=14)
        tk.Button(big, text="🧹   TOUT NETTOYER",
                  command=self.run_clean_all, font=("Segoe UI", 11, "bold"),
                  bg=PURPLE, fg="white", activebackground="#d0a8ff",
                  relief=tk.FLAT, cursor="hand2", pady=13).pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    #  ONGLET RÉSEAU                                                       #
    # ------------------------------------------------------------------ #
    def build_network(self):
        f = self.make_scroll(self.tab_net)

        card = tk.Frame(f, bg=CARD)
        card.pack(fill=tk.X, padx=16, pady=8)
        tk.Label(card, text="📡  TEST DE CONNEXION", font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=ACCENT).pack(anchor=tk.W, padx=14, pady=(10, 2))
        tk.Frame(card, bg=ACCENT, height=2).pack(fill=tk.X, padx=14, pady=(0, 8))
        row = tk.Frame(card, bg=CARD)
        row.pack(fill=tk.X, padx=14, pady=(0, 12))
        tk.Button(row, text="🏓  Tester le ping (latence)", command=self.run_ping,
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", pady=9, padx=12).pack(side=tk.LEFT, padx=4)
        tk.Button(row, text="🌍  Afficher mes infos IP", command=self.run_ipinfo,
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", pady=9, padx=12).pack(side=tk.LEFT, padx=4)

        g = self.card_section(f, "🌐  CONFIGURATION RÉSEAU")
        for i, (t, c) in enumerate([
            ("DNS → Cloudflare (1.1.1.1)", self.run_dns_cloudflare),
            ("DNS → Google (8.8.8.8)", self.run_dns_google),
            ("DNS → Automatique (défaut)", self.run_dns_auto),
            ("Désactiver auto-tuning TCP", self.run_autotuning),
            ("Optimiser TCP/IP (QoS)", self.run_tcpip),
            ("Désactiver IPv6", self.run_ipv6),
            ("Optimiser adaptateur réseau", self.run_nic_opt),
            ("Réinitialiser la pile réseau", self.run_net_reset)]):
            self.grid_btn(g, i, t, c)

    # ------------------------------------------------------------------ #
    #  ONGLET PROCESSUS                                                    #
    # ------------------------------------------------------------------ #
    def build_processes(self):
        p = self.tab_proc
        top = tk.Frame(p, bg=BG)
        top.pack(fill=tk.X, padx=16, pady=10)
        tk.Label(top, text="🔥  Processus les plus gourmands",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Button(top, text="🔄  Rafraîchir", command=self.refresh_processes,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="⛔  Terminer le processus", command=self.kill_process,
                  font=("Segoe UI", 8), bg=BG3, fg=ERROR, relief=tk.FLAT,
                  cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=4)

        cols = ("pid", "nom", "cpu", "ram")
        self.proc_tree = ttk.Treeview(p, columns=cols, show="headings", height=18)
        for c, w, txt in [("pid", 80, "PID"), ("nom", 320, "Nom du processus"),
                          ("cpu", 110, "CPU %"), ("ram", 130, "Mémoire (Mo)")]:
            self.proc_tree.heading(c, text=txt)
            self.proc_tree.column(c, width=w, anchor=tk.W if c == "nom" else tk.CENTER)
        self.proc_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        self.refresh_processes()

    def refresh_processes(self):
        if not HAS_PSUTIL:
            self.log("⚠  psutil non installé — onglet processus indisponible.")
            return
        def task():
            procs = []
            for pr in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    pr.cpu_percent(None)
                except:
                    pass
            time.sleep(0.5)
            for pr in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    cpu = pr.cpu_percent(None) / (psutil.cpu_count() or 1)
                    mem = pr.info["memory_info"].rss / (1024*1024)
                    procs.append((pr.info["pid"], pr.info["name"] or "?", cpu, mem))
                except:
                    pass
            procs.sort(key=lambda x: x[3], reverse=True)
            def fill():
                self.proc_tree.delete(*self.proc_tree.get_children())
                for pid, name, cpu, mem in procs[:40]:
                    self.proc_tree.insert("", tk.END,
                        values=(pid, name, f"{cpu:.1f}", f"{mem:.0f}"))
            self.root.after(0, fill)
        threading.Thread(target=task, daemon=True).start()

    def kill_process(self):
        if not HAS_PSUTIL:
            return
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showinfo("Processus", "Sélectionnez d'abord un processus.")
            return
        vals = self.proc_tree.item(sel[0])["values"]
        pid, name = vals[0], vals[1]
        if not messagebox.askyesno("Terminer le processus",
            f"Voulez-vous vraiment terminer :\n\n{name} (PID {pid}) ?"):
            return
        try:
            psutil.Process(int(pid)).terminate()
            self.log(f"✓  Processus terminé : {name} (PID {pid})")
            self.write_log(f"Processus terminé : {name} (PID {pid})")
            self.refresh_processes()
        except Exception as e:
            self.log(f"✗  Impossible de terminer {name} : {e}")

    # ------------------------------------------------------------------ #
    #  ONGLET DÉMARRAGE                                                    #
    # ------------------------------------------------------------------ #
    def build_startup(self):
        p = self.tab_startup
        top = tk.Frame(p, bg=BG)
        top.pack(fill=tk.X, padx=16, pady=10)
        tk.Label(top, text="🚀  Programmes lancés au démarrage de Windows",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Button(top, text="🔄  Rafraîchir", command=self.refresh_startup,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="⛔  Retirer du démarrage", command=self.remove_startup,
                  font=("Segoe UI", 8), bg=BG3, fg=ERROR, relief=tk.FLAT,
                  cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=4)

        tk.Label(p, text="ℹ  Retirer un programme du démarrage l'empêche de se "
                 "lancer automatiquement (il reste installé).",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor=tk.W, padx=16)

        cols = ("nom", "emplacement", "commande")
        self.startup_tree = ttk.Treeview(p, columns=cols, show="headings", height=16)
        for c, w, txt in [("nom", 220, "Programme"),
                          ("emplacement", 130, "Source"),
                          ("commande", 480, "Chemin / Commande")]:
            self.startup_tree.heading(c, text=txt)
            self.startup_tree.column(c, width=w, anchor=tk.W)
        self.startup_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 12))
        self.refresh_startup()

    def _startup_keys(self):
        return [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        ]

    def refresh_startup(self):
        if not HAS_WINREG:
            return
        self.startup_tree.delete(*self.startup_tree.get_children())
        for hive, path, label in self._startup_keys():
            try:
                key = winreg.OpenKey(hive, path)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        self.startup_tree.insert("", tk.END,
                            values=(name, label, value))
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except:
                pass

    def remove_startup(self):
        sel = self.startup_tree.selection()
        if not sel:
            messagebox.showinfo("Démarrage", "Sélectionnez d'abord un programme.")
            return
        vals = self.startup_tree.item(sel[0])["values"]
        name, label = vals[0], vals[1]
        if not messagebox.askyesno("Retirer du démarrage",
            f"Retirer « {name} » du démarrage Windows ?"):
            return
        hive = winreg.HKEY_CURRENT_USER if label == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            self.log(f"✓  « {name} » retiré du démarrage.")
            self.write_log(f"Retiré du démarrage : {name}")
            self.refresh_startup()
        except Exception as e:
            self.log(f"✗  Erreur : {e}")

    # ------------------------------------------------------------------ #
    #  ONGLET CONFIDENTIALITÉ                                              #
    # ------------------------------------------------------------------ #
    def build_privacy(self):
        f = self.make_scroll(self.tab_priv)
        g = self.card_section(f, "🔒  CONFIDENTIALITÉ & TÉLÉMÉTRIE", PURPLE)
        for i, (t, c) in enumerate([
            ("Désactiver télémétrie Windows", self.run_telemetry),
            ("Désactiver Cortana", self.run_cortana),
            ("Désactiver publicités Windows", self.run_ads),
            ("Désactiver Activity History", self.run_activity),
            ("Désactiver localisation", self.run_location),
            ("Désactiver diagnostics & feedback", self.run_diag),
            ("Désactiver suggestions démarrage", self.run_start_sugg),
            ("Désactiver l'ID de publicité", self.run_advertising_id)]):
            self.grid_btn(g, i, t, c, PURPLE)

        big = tk.Frame(f, bg=BG)
        big.pack(fill=tk.X, padx=16, pady=14)
        tk.Button(big, text="🔒   Appliquer les réglages confidentialité recommandés",
                  command=self.run_privacy_all, font=("Segoe UI", 11, "bold"),
                  bg=PURPLE, fg="white", activebackground="#d0a8ff",
                  relief=tk.FLAT, cursor="hand2", pady=13).pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    #  ONGLET RAPPORT                                                      #
    # ------------------------------------------------------------------ #
    def build_report(self):
        p = self.tab_report
        card = tk.Frame(p, bg=CARD)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Label(card, text="📄  Rapport système", font=("Segoe UI", 13, "bold"),
                 bg=CARD, fg=ACCENT).pack(anchor=tk.W, padx=20, pady=(20, 4))
        tk.Label(card,
                 text="Génère un rapport HTML complet de votre configuration "
                 "(matériel, disques, réseau) enregistré sur le Bureau.",
                 font=("Segoe UI", 9), bg=CARD, fg=MUTED, justify=tk.LEFT
                 ).pack(anchor=tk.W, padx=20, pady=(0, 16))
        tk.Button(card, text="📊  Générer le rapport HTML",
                  command=self.generate_report, font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg=BG, activebackground="#33ddff",
                  relief=tk.FLAT, cursor="hand2", pady=11, padx=20
                  ).pack(anchor=tk.W, padx=20)
        tk.Button(card, text="📁  Ouvrir le fichier journal (.log)",
              command=self.open_log, font=("Segoe UI", 9),
              bg=BG3, fg=TEXT, relief=tk.FLAT, cursor="hand2",
              pady=9, padx=20).pack(anchor=tk.W, padx=20, pady=10)
        tk.Frame(card, bg=BG3, height=1).pack(fill=tk.X, padx=20, pady=14)
        tk.Label(card, text=f"🔄  Version installée : {VERSION}",
                 font=("Segoe UI", 9, "bold"), bg=CARD, fg=ACCENT2
                 ).pack(anchor=tk.W, padx=20)
        tk.Button(card, text="🔍  Vérifier les mises à jour",
                  command=lambda: self.check_update(silent=False),
                  font=("Segoe UI", 10, "bold"), bg=SUCCESS, fg=BG,
                  activebackground="#5fd970", relief=tk.FLAT,
                  cursor="hand2", pady=11, padx=20
                  ).pack(anchor=tk.W, padx=20, pady=10)

        # --- Sauvegarde / Restauration des réglages (P2.2) ---
        bk = tk.Frame(p, bg=CARD)
        bk.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Label(bk, text="💾  Sauvegarde / Restauration des réglages",
                 font=("Segoe UI", 11, "bold"), bg=CARD, fg=PURPLE
                 ).pack(anchor=tk.W, padx=20, pady=(14, 2))
        tk.Label(bk,
                 text="Sauvegarde l'état actuel des valeurs de registre et "
                 "des services modifiés par l'application, puis permet de les "
                 "restaurer. Ne couvre pas les fichiers supprimés, ResetBase "
                 "ni la réinitialisation réseau.",
                 font=("Segoe UI", 9), bg=CARD, fg=MUTED, justify=tk.LEFT,
                 wraplength=720).pack(anchor=tk.W, padx=20, pady=(0, 10))
        bkrow = tk.Frame(bk, bg=CARD)
        bkrow.pack(anchor=tk.W, padx=20, pady=(0, 16))
        tk.Button(bkrow, text="💾  Créer une sauvegarde (registre/services)",
                  command=self.create_backup, font=("Segoe UI", 9, "bold"),
                  bg=BG3, fg=PURPLE, relief=tk.FLAT, cursor="hand2",
                  pady=10, padx=14).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(bkrow, text="↩️  Restaurer la dernière sauvegarde",
                  command=self.restore_latest_backup, font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT, relief=tk.FLAT, cursor="hand2",
                  pady=10, padx=14).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    #  ONGLET AIDE (recherche dans les descriptions de boutons)            #
    # ------------------------------------------------------------------ #
    def build_help(self):
        p = self.tab_help

        # En-tête
        head = tk.Frame(p, bg=BG)
        head.pack(fill=tk.X, padx=16, pady=(12, 4))
        tk.Label(head, text="❓  Aide — Que fait chaque bouton ?",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=ACCENT
                 ).pack(anchor=tk.W)
        tk.Label(head, text="Survolez n'importe quel bouton de l'application "
                 "pour voir sa description. Vous pouvez aussi chercher ci-dessous.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED, justify=tk.LEFT
                 ).pack(anchor=tk.W, pady=(2, 0))

        # Barre de recherche
        searchbar = tk.Frame(p, bg=BG3)
        searchbar.pack(fill=tk.X, padx=16, pady=(8, 4))
        tk.Label(searchbar, text="🔍", font=("Segoe UI", 11),
                 bg=BG3, fg=ACCENT).pack(side=tk.LEFT, padx=(10, 4), pady=8)
        self.help_search_var = tk.StringVar()
        self.help_search_var.trace_add("write", lambda *a: self._draw_help_list())
        entry = tk.Entry(searchbar, textvariable=self.help_search_var,
                         font=("Segoe UI", 10), bg=BG2, fg=TEXT,
                         insertbackground=TEXT, relief=tk.FLAT)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), pady=6,
                   ipady=4)
        tk.Button(searchbar, text="✕  Effacer", command=self._clear_help_search,
                  font=("Segoe UI", 8), bg=BG3, fg=MUTED, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.RIGHT, padx=(0, 8))

        # Compteur
        self.help_count = tk.Label(p, text="", font=("Segoe UI", 8),
                                   bg=BG, fg=MUTED, anchor=tk.W)
        self.help_count.pack(fill=tk.X, padx=18, pady=(0, 2))

        # Zone défilante (Canvas + Scrollbar)
        container = tk.Frame(p, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        self._help_canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL,
                           command=self._help_canvas.yview)
        self.help_list_frame = tk.Frame(self._help_canvas, bg=BG)
        self.help_list_frame.bind(
            "<Configure>",
            lambda e: self._help_canvas.configure(
                scrollregion=self._help_canvas.bbox("all")))
        cw = self._help_canvas.create_window(
            (0, 0), window=self.help_list_frame, anchor=tk.NW)
        self._help_canvas.bind(
            "<Configure>",
            lambda e: self._help_canvas.itemconfig(cw, width=e.width))
        self._help_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._help_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _wheel(e):
            self._help_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"
        self._help_wheel = _wheel
        self._help_canvas.bind("<MouseWheel>", _wheel)

        self._draw_help_list()

    def _clear_help_search(self):
        self.help_search_var.set("")

    def _draw_help_list(self):
        """Affiche — ou filtre selon la recherche — la liste des descriptions."""
        if not hasattr(self, "help_list_frame"):
            return
        for child in self.help_list_frame.winfo_children():
            child.destroy()

        raw = self.help_search_var.get().strip()
        query = raw.lower()
        items = [(label, desc) for label, desc in ACTION_TIPS.items()
                 if not query or query in label.lower() or query in desc.lower()]

        for label, desc in items:
            cardf = tk.Frame(self.help_list_frame, bg=CARD)
            cardf.pack(fill=tk.X, padx=4, pady=4)
            tk.Label(cardf, text=label, font=("Segoe UI", 10, "bold"),
                     bg=CARD, fg=ACCENT, anchor=tk.W, justify=tk.LEFT
                     ).pack(fill=tk.X, padx=12, pady=(8, 2))
            tk.Label(cardf, text=desc, font=("Segoe UI", 9),
                     bg=CARD, fg=MUTED, anchor=tk.W, justify=tk.LEFT,
                     wraplength=1000).pack(fill=tk.X, padx=12, pady=(0, 10))

        if not items:
            tk.Label(self.help_list_frame,
                     text=f"Aucun résultat pour « {raw} ».",
                     font=("Segoe UI", 10), bg=BG, fg=MUTED
                     ).pack(anchor=tk.W, padx=8, pady=20)

        if hasattr(self, "help_count"):
            total = len(ACTION_TIPS)
            self.help_count.config(
                text=(f"{len(items)} résultat(s) sur {total}" if query
                      else f"{total} actions documentées"))

        # Réattache la molette aux nouveaux enfants
        if hasattr(self, "_help_wheel"):
            def _bind(w):
                w.bind("<MouseWheel>", self._help_wheel)
                for c in w.winfo_children():
                    _bind(c)
            _bind(self.help_list_frame)

    # ================================================================== #
    #  MONITORING                                                          #
    # ================================================================== #
    def start_monitor(self):
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def monitor_loop(self):
        while self.monitoring:
            try:
                if HAS_PSUTIL:
                    cpu = psutil.cpu_percent(interval=1)
                    ram = psutil.virtual_memory().percent
                    disk = psutil.disk_usage("C:\\").percent
                else:
                    cpu = ram = disk = 0
                    time.sleep(1)
                self.cpu_history.append(cpu)
                self.cpu_history = self.cpu_history[-60:]
                # Lecture GPU via compteurs Windows — coûteuse, donc ~toutes les 2 s.
                # On garde la dernière valeur connue entre deux lectures.
                self._gpu_tick += 1
                if self._gpu_tick % 2 == 1:
                    g = self.gpu_monitor.read_percent()
                    if g is not None:
                        self._last_gpu = g
                self.root.after(0, lambda c=cpu, r=ram, d=disk: self.update_gauges(c, r, d))
            except:
                time.sleep(1)

    def update_gauges(self, cpu, ram, disk):
        try:
            self.draw_gauge("cpu", cpu)
            self.draw_gauge("gpu", self._last_gpu)
            self.draw_gauge("ram", ram)
            self.draw_gauge("disk", disk)
            self.draw_graph()
        except:
            pass
        # Met à jour le tooltip du tray avec les stats temps réel
        if self.tray_icon:
            try:
                self.tray_icon.title = (
                    f"PC Optimizer Pro v{VERSION}\n"
                    f"CPU: {cpu:.0f}%  RAM: {ram:.0f}%  Disque: {disk:.0f}%"
                )
            except:
                pass
        # Vérifie les alertes (couleur icône + notification Windows)
        self._check_alerts(cpu, ram, disk)
        # Sauvegarde l'historique toutes les 60 secondes
        if time.time() - self._last_history_save > 60:
            self._save_history_entry(cpu, ram, disk)
            self._last_history_save = time.time()

    def load_sysinfo(self):
        def fetch():
            def cim(cls, prop):
                """Get-CimInstance — remplace wmic (déprécié sur Windows 11 récent)."""
                try:
                    cmd = (f'powershell -NoProfile -Command '
                           f'"(Get-CimInstance {cls} | '
                           f'Select-Object -First 1 -ExpandProperty {prop})"')
                    r = subprocess.check_output(cmd, shell=True, text=True,
                            encoding="utf-8", errors="replace", timeout=15,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                    return r.strip() or "N/A"
                except:
                    return "N/A"
            data = {
                "Système": platform.system() + " " + platform.release(),
                "Processeur": cim("Win32_Processor", "Name")[:48],
                "Carte graphique": cim("Win32_VideoController", "Name")[:48],
                "Nom du PC": platform.node(),
                "Utilisateur": os.getenv("USERNAME", "?"),
            }
            if HAS_PSUTIL:
                vm = psutil.virtual_memory()
                data["Mémoire totale"] = f"{vm.total/(1024**3):.1f} Go"
                du = psutil.disk_usage("C:\\")
                data["Disque C:"] = (f"{du.free/(1024**3):.0f} Go libres "
                                     f"/ {du.total/(1024**3):.0f} Go")
                boot = datetime.datetime.fromtimestamp(psutil.boot_time())
                delta = datetime.datetime.now() - boot
                h, m = divmod(delta.seconds // 60, 60)
                data["Démarré depuis"] = f"{delta.days}j {h}h {m}min"
            else:
                data["Mémoire totale"] = "psutil requis"
                data["Disque C:"] = "psutil requis"
                data["Démarré depuis"] = "psutil requis"
            for k, v in data.items():
                if k in self.info_labels:
                    self.root.after(0, lambda k=k, v=v:
                                    self.info_labels[k].config(text=v))
        threading.Thread(target=fetch, daemon=True).start()

    # ================================================================== #
    #  CONSOLE                                                             #
    # ================================================================== #
    def log(self, text):
        def _log():
            self.console.configure(state=tk.NORMAL)
            self.console.insert(tk.END, text + "\n")
            self.console.see(tk.END)
            self.console.configure(state=tk.DISABLED)
        self.root.after(0, _log)

    def set_status(self, txt):
        self.root.after(0, lambda: self.status_var.set(txt))

    def clear_console(self):
        self.console.configure(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.configure(state=tk.DISABLED)

    def copy_console(self):
        try:
            txt = self.console.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.set_status("✓  Console copiée dans le presse-papiers")
        except Exception as e:
            self.log(f"✗  {e}")

    def save_console(self):
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.isdir(desktop):
                desktop = os.path.expanduser("~")
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(desktop, f"console_pcoptimizer_{stamp}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.console.get(1.0, tk.END))
            self.log(f"✓  Console enregistrée : {path}")
        except Exception as e:
            self.log(f"✗  {e}")

    # ================================================================== #
    #  REDÉMARRER / ARRÊTER                                                #
    # ================================================================== #
    def reboot_pc(self):
        if messagebox.askyesno("Redémarrer",
                "Redémarrer l'ordinateur maintenant ?\n"
                "Pensez à enregistrer votre travail."):
            subprocess.Popen("shutdown /r /t 5", shell=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            self.log("⚠  Redémarrage dans 5 secondes…")

    def shutdown_pc(self):
        if messagebox.askyesno("Arrêter",
                "Éteindre l'ordinateur maintenant ?\n"
                "Pensez à enregistrer votre travail."):
            subprocess.Popen("shutdown /s /t 5", shell=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            self.log("⚠  Arrêt dans 5 secondes…")

    # ================================================================== #
    #  EXÉCUTION DE COMMANDES                                              #
    # ================================================================== #
    def _confirm(self, titre, message, danger=False):
        """Demande une confirmation avant une action sensible.
        Renvoie True si l'utilisateur accepte. En cas d'erreur d'affichage,
        renvoie False (on bloque par sécurité)."""
        try:
            return messagebox.askyesno(
                titre, message,
                icon=("warning" if danger else "question"))
        except Exception:
            return False

    def _decode_line(self, data):
        """Décode une ligne en testant plusieurs encodages — UTF-16-LE/BE pour SFC."""
        # SFC.exe écrit en UTF-16 : on teste LE et BE et on garde le meilleur
        if len(data) >= 4 and data.count(b"\x00") >= len(data) // 3:
            best = None
            best_score = -1
            for enc in ("utf-16-le", "utf-16-be"):
                try:
                    decoded = data.decode(enc, errors="replace").replace("\x00", "")
                    # Score : nb de caractères ASCII imprimables + accents FR
                    score = sum(1 for c in decoded
                                if (32 <= ord(c) <= 126)
                                or c in "éèàçùâêîôûäëïöüÉÈÀÇÙ\t\r\n")
                    if score > best_score:
                        best_score = score
                        best = decoded
                except Exception:
                    continue
            if best is not None and best_score >= len(best.strip()) * 0.5:
                return best
        # Fallback : encodages classiques (UTF-8 → cp850 → cp1252)
        for enc in ("utf-8", "cp850", "cp1252"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def _exec(self, cmd, label):
        self.set_status(f"⏳  {label}…")
        self.write_log(f"DÉBUT : {label}")
        self.log(f"\n{'═'*60}\n▶  {label}\n{'═'*60}")
        # CORRECTION encodage : on force la console en UTF-8 pour les commandes cmd
        if not cmd.strip().lower().startswith("powershell"):
            cmd = f"chcp 65001 >nul 2>&1 & {cmd}"
        try:
            proc = subprocess.Popen(cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            # CORRECTION UTF-16 : on lit TOUT le flux en binaire, puis on décode
            # le bloc complet d'un seul coup. Lire ligne par ligne cassait
            # l'alignement UTF-16 de SFC/DISM : l'octet nul du saut de ligne
            # (0A 00) se reportait sur la ligne suivante et corrompait accents
            # et apostrophes (« l⁡nalyse », « d⁩ntégrité », « � »…).
            raw = proc.stdout.read()
            proc.wait()
            text = self._decode_line(raw).replace("\ufeff", "")
            for line in text.splitlines():
                line = line.rstrip()
                if line:
                    self.log(line)
            ok = proc.returncode == 0
            note = ""
            if not ok:
                low = text.lower()
                if ("1062" in text or "n'a pas été démarré" in low
                        or "has not been started" in low
                        or "not been started" in low):
                    note = "  (service déjà arrêté — sans conséquence)"
                    ok = True
                elif ("1060" in text or "n'existe pas" in low
                      or "does not exist" in low
                      or "introuvable" in low):
                    note = "  (élément déjà absent — sans conséquence)"
                    ok = True
            self.log(f"{'✓' if ok else '⚠'}  {label} — "
                     f"{'Succès' if ok else f'Code {proc.returncode}'}{note}\n")
            self.write_log(f"FIN : {label} ({'OK' if ok else 'code '+str(proc.returncode)})")
        except Exception as e:
            self.log(f"✗  Erreur : {e}\n")
            self.write_log(f"ERREUR : {label} — {e}")
        self.set_status("✓  Prêt")

    def run_cmd(self, cmd, label):
        threading.Thread(target=self._exec, args=(cmd, label), daemon=True).start()

    def _ps(self, s):
        """CORRECTION : encode en Base64 + force UTF-8 pour les accents."""
        full = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + s
        encoded = base64.b64encode(full.encode("utf-16-le")).decode()
        return f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"

    def run_ps(self, s, label, modify=True):
        cmd = self._ps(s)
        if modify:
            self._run_with_restore_point(cmd, label)
        else:
            self.run_cmd(cmd, label)

    def _run_with_restore_point(self, cmd, label):
        """Propose UNE FOIS par session de créer un point de restauration
        Windows avant la première modification système, puis exécute la commande.
        Note : Windows peut ignorer la création si un point a déjà été créé
        dans les dernières 24 h (limite système) — c'est normal."""
        create_rp = False
        if not self._restore_point_offered:
            self._restore_point_offered = True
            try:
                create_rp = messagebox.askyesno(
                    "Point de restauration",
                    "Vous allez modifier des réglages système.\n\n"
                    "Créer d'abord un point de restauration Windows ?\n"
                    "(Recommandé — proposé une seule fois par session.)")
            except Exception:
                create_rp = False

        def worker():
            if create_rp:
                self._exec(
                    self._ps('Checkpoint-Computer -Description '
                             '"PC Optimizer (auto)" '
                             '-RestorePointType MODIFY_SETTINGS'),
                    "Point de restauration (auto)")
            self._exec(cmd, label)
        threading.Thread(target=worker, daemon=True).start()

    def has_winget(self):
        """CORRECTION : méthode ajoutée (référencée par run_winget)."""
        try:
            r = subprocess.run("winget --version", shell=True,
                               capture_output=True, timeout=6,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            return r.returncode == 0
        except:
            return False

    # ================================================================== #
    #  ACTIONS                                                             #
    # ================================================================== #
    def run_restore_point(self):
        self.run_ps('Checkpoint-Computer -Description "PC Optimizer" '
                    '-RestorePointType MODIFY_SETTINGS',
                    "Point de restauration", modify=False)

    def run_sfc(self):
        self.run_cmd("sfc /scannow", "SFC — Fichiers système")

    def run_dism(self):
        self.run_cmd("DISM /Online /Cleanup-Image /RestoreHealth",
                     "DISM — Image Windows")

    def run_chkdsk(self):
        if not self._confirm("ChkDsk — Planifier (C:)",
                "Une vérification complète du disque C: sera planifiée au "
                "prochain redémarrage de Windows.\n\n"
                "Elle peut allonger le temps de démarrage. Continuer ?"):
            return
        self.run_cmd("echo Y | chkdsk C: /f /r", "ChkDsk — Planification C:")

    def run_registry_repair(self):
        self.run_cmd("DISM /Online /Cleanup-Image /ScanHealth",
                     "Registre — Vérification image")

    def run_winget(self):
        if not self.has_winget():
            self.log("✗  winget n'est pas disponible sur ce PC.")
            return
        self.run_cmd("winget upgrade --all --silent "
                     "--accept-source-agreements --accept-package-agreements",
                     "Winget — Mise à jour logiciels")

    def run_drivers_wu(self):
        self.run_ps("Install-Module PSWindowsUpdate -Force -Scope CurrentUser "
                    "-EA SilentlyContinue; Import-Module PSWindowsUpdate; "
                    "Get-WindowsUpdate -Category Drivers -Install -AcceptAll -IgnoreReboot",
                    "Pilotes — Windows Update")

    def run_nvidia(self):
        """CORRECTION : ouvre la page de téléchargement officielle NVIDIA App."""
        import webbrowser
        self.log("\n▶  NVIDIA App — Ouverture de la page de téléchargement")
        self.log("ℹ  NVIDIA App remplace officiellement GeForce Experience.")
        try:
            webbrowser.open("https://www.nvidia.com/fr-fr/software/nvidia-app/")
            self.log("✓  Page ouverte dans votre navigateur.")
        except Exception as e:
            self.log(f"✗  Erreur : {e}")

    def run_amd(self):
        """CORRECTION : ouvre la page de téléchargement officielle AMD Adrenalin."""
        import webbrowser
        self.log("\n▶  AMD Adrenalin — Ouverture de la page de téléchargement")
        try:
            webbrowser.open("https://www.amd.com/fr/support/download/drivers.html")
            self.log("✓  Page ouverte dans votre navigateur.")
        except Exception as e:
            self.log(f"✗  Erreur : {e}")

    def run_detect_gpu(self):
        def task():
            self.log("\n▶  Détection de la carte graphique…")
            try:
                r = subprocess.check_output(
                    'powershell -NoProfile -Command '
                    '"[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;'
                    '(Get-CimInstance Win32_VideoController).Name"',
                    shell=True, text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW).lower()
                if "nvidia" in r:
                    self.log("✓  GPU NVIDIA détecté")
                    self.root.after(0, self.run_nvidia)
                elif "amd" in r or "radeon" in r:
                    self.log("✓  GPU AMD détecté")
                    self.root.after(0, self.run_amd)
                elif "intel" in r:
                    self.log("ℹ  GPU Intel détecté — utilisez Windows Update "
                             "pour les pilotes Intel.")
                else:
                    self.log("⚠  GPU non reconnu automatiquement.")
            except Exception as e:
                self.log(f"✗  Erreur détection : {e}")
        threading.Thread(target=task, daemon=True).start()

    def run_runtimes(self):
        """CORRECTION : code mort après return supprimé."""
        self.run_cmd("winget install --id=Microsoft.VCRedist.2015+.x64 -e --silent "
                     "--accept-source-agreements --accept-package-agreements && "
                     "winget install --id=Microsoft.DotNet.Runtime.8 -e --silent "
                     "--accept-source-agreements --accept-package-agreements",
                     "Runtimes — VC++ & .NET")

    def run_power_plan(self):
        self.run_cmd("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                     "Plan Haute Performance")

    def run_ultimate_power(self):
        self.run_cmd("powercfg /duplicatescheme "
                     "e9a42b02-d5df-448d-aa00-03f14749eb61 && "
                     "powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61",
                     "Plan Ultimate Performance")

    def run_game_mode(self):
        self.run_ps('Set-ItemProperty "HKCU:\\Software\\Microsoft\\GameBar" '
                    '-Name "AutoGameModeEnabled" -Value 1; '
                    'Set-ItemProperty "HKCU:\\Software\\Microsoft\\GameBar" '
                    '-Name "AllowAutoGameMode" -Value 1; Write-Host "Game Mode activé"',
                    "Game Mode")

    def run_hags(self):
        self.run_ps('Set-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet\\Control'
                    '\\GraphicsDrivers" -Name "HwSchMode" -Value 2; '
                    'Write-Host "HAGS activé"', "HAGS")

    def run_mouse(self):
        self.run_ps('Set-ItemProperty "HKCU:\\Control Panel\\Mouse" '
                    '-Name "MouseSpeed" -Value "0"; '
                    'Set-ItemProperty "HKCU:\\Control Panel\\Mouse" '
                    '-Name "MouseThreshold1" -Value "0"; '
                    'Set-ItemProperty "HKCU:\\Control Panel\\Mouse" '
                    '-Name "MouseThreshold2" -Value "0"; '
                    'Write-Host "Accélération souris désactivée"', "Souris")

    def run_nagle(self):
        self.run_ps('Get-ChildItem "HKLM:\\SYSTEM\\CurrentControlSet\\Services'
                    '\\Tcpip\\Parameters\\Interfaces" | ForEach-Object { '
                    'Set-ItemProperty $_.PSPath -Name "TcpAckFrequency" -Value 1 '
                    '-EA SilentlyContinue; Set-ItemProperty $_.PSPath '
                    '-Name "TCPNoDelay" -Value 1 -EA SilentlyContinue }; '
                    'Write-Host "Nagle désactivé"', "Nagle Algorithm")

    def run_priority(self):
        self.run_ps('$p="HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'
                    '\\Multimedia\\SystemProfile"; '
                    'Set-ItemProperty "$p\\Tasks\\Games" -Name "Priority" -Value 6; '
                    'Set-ItemProperty "$p\\Tasks\\Games" '
                    '-Name "Scheduling Category" -Value "High"; '
                    'Set-ItemProperty "$p" -Name "SystemResponsiveness" -Value 0; '
                    'Write-Host "Priorité gaming appliquée"', "Priorité CPU/GPU")

    def run_gamebar(self):
        self.run_ps('Set-ItemProperty "HKCU:\\Software\\Microsoft\\GameBar" '
                    '-Name "UseNexusForGameBarEnabled" -Value 0; '
                    'Write-Host "Game Bar désactivée"', "Xbox Game Bar")

    def run_dvr(self):
        self.run_ps('Set-ItemProperty "HKCU:\\System\\GameConfigStore" '
                    '-Name "GameDVR_Enabled" -Value 0; '
                    'New-Item "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows'
                    '\\GameDVR" -Force -EA SilentlyContinue | Out-Null; '
                    'Set-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft'
                    '\\Windows\\GameDVR" -Name "AllowGameDVR" -Value 0; '
                    'Write-Host "DVR désactivé"', "Capture/DVR")

    def run_animations(self):
        self.run_ps('Set-ItemProperty "HKCU:\\Software\\Microsoft\\Windows'
                    '\\CurrentVersion\\Explorer\\VisualEffects" '
                    '-Name "VisualFXSetting" -Value 2; '
                    'Write-Host "Animations désactivées"', "Animations Windows")

    def run_timer(self):
        self.run_cmd("bcdedit /set useplatformtick yes && "
                     "bcdedit /deletevalue useplatformclock", "Timer 1ms")

    def run_registry_gaming(self):
        k = ('HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'
             '\\Multimedia\\SystemProfile\\Tasks\\Games')
        self.run_ps(f'New-Item "{k}" -Force -EA SilentlyContinue | Out-Null; '
                    f'Set-ItemProperty "{k}" -Name "GPU Priority" -Value 8; '
                    f'Set-ItemProperty "{k}" -Name "Priority" -Value 6; '
                    f'Set-ItemProperty "{k}" -Name "Clock Rate" -Value 10000; '
                    'Write-Host "Tweaks registre gaming appliqués"',
                    "Registre Gaming avancé")

    def run_clear_standby(self):
        """Libère la mémoire des processus inactifs (pas la standby list Windows)."""
        self.log("\nℹ  Note : vider la vraie « standby list » de Windows "
                 "nécessite un outil bas niveau (type RAMMap). Ce bouton "
                 "libère seulement la mémoire de travail des processus, "
                 "ce qui est sûr et suffisant dans la majorité des cas.")
        self.run_ps(
            "$before = (Get-CimInstance Win32_OperatingSystem)."
            "FreePhysicalMemory; "
            "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers(); "
            "Start-Sleep -Milliseconds 500; "
            "$after = (Get-CimInstance Win32_OperatingSystem)."
            "FreePhysicalMemory; "
            "Write-Host ('Mémoire libre : ' + "
            "[math]::Round($before/1MB,2) + ' Go -> ' + "
            "[math]::Round($after/1MB,2) + ' Go')",
            "Mémoire — Libération des processus inactifs", modify=False)

    def run_mem_compression(self):
        self.run_ps("Disable-MMAgent -mc; Write-Host 'Compression désactivée'",
                    "Compression mémoire")

    def run_large_cache(self):
        self.run_ps('Set-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet\\Control'
                    '\\Session Manager\\Memory Management" '
                    '-Name "LargeSystemCache" -Value 1; Write-Host "Activé"',
                    "Large System Cache")

    def run_sysmain(self):
        self.run_cmd("sc stop SysMain >nul 2>&1 & sc config SysMain start=disabled",
                     "SysMain")

    def run_wsearch(self):
        self.run_cmd("sc stop WSearch >nul 2>&1 & sc config WSearch start=disabled",
                     "Windows Search")

    def run_hibernation(self):
        self.run_cmd("powercfg /h off", "Hibernation")

    def run_wer(self):
        self.run_cmd("sc stop WerSvc >nul 2>&1 & sc config WerSvc start=disabled",
                     "Windows Error Reporting")

    def run_boot_opt(self):
        self.run_cmd("bcdedit /set bootmenupolicy standard && "
                     "bcdedit /set quietboot yes && bcdedit /timeout 5",
                     "Optimisation du démarrage")

    # --- Nettoyage ---
    def run_clean_temp(self):
        self.run_cmd('cmd /c "del /q /f /s %TEMP%\\* 2>nul & '
                     'del /q /f /s C:\\Windows\\Temp\\* 2>nul"',
                     "Fichiers temporaires")

    def run_clean_bin(self):
        if not self._confirm("Vider la Corbeille",
                "Vider la Corbeille Windows ?\n\n"
                "Les fichiers ne pourront plus être récupérés."):
            return
        self.run_ps("Clear-RecycleBin -Force", "Corbeille", modify=False)

    def run_dns(self):
        self.run_cmd("ipconfig /flushdns", "Cache DNS")

    def run_disk_opt(self):
        self.run_ps("Optimize-Volume -DriveLetter C -Verbose", "Optimisation disque",
                    modify=False)

    def run_prefetch(self):
        self.run_cmd('cmd /c "del /q /f /s C:\\Windows\\Prefetch\\* 2>nul"',
                     "Prefetch")

    def run_cleanmgr(self):
        self.run_cmd("cleanmgr /sageset:1 & cleanmgr /sagerun:1",
                     "Disk Cleanup")

    def run_store_cache(self):
        self.run_cmd("wsreset.exe", "Cache Windows Store")

    def run_clean_winsxs(self):
        if not self._confirm("Nettoyer composants anciens",
                "⚠  ACTION IRRÉVERSIBLE\n\n"
                "Après cette opération, les mises à jour Windows déjà "
                "installées ne pourront PLUS être désinstallées.\n\n"
                "Êtes-vous sûr de vouloir continuer ?", danger=True):
            return
        self.run_cmd("DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase",
                     "Composants Windows anciens")

    def run_thumb_cache(self):
        self.run_cmd('cmd /c "del /q /f /s %LocalAppData%\\Microsoft\\Windows'
                     '\\Explorer\\thumbcache_*.db 2>nul"', "Cache miniatures")

    def run_event_logs(self):
        if not self._confirm("Vider les logs d'événements",
                "⚠  Tous les journaux d'événements Windows seront supprimés.\n\n"
                "Vous perdrez l'historique de diagnostic du système "
                "(utile en cas de dépannage). Continuer ?", danger=True):
            return
        self.run_ps('wevtutil el | ForEach-Object { '
                    'wevtutil cl "$_" 2>$null }; '
                    'Write-Host "Journaux d evenements vides"',
                    "Journaux d'événements", modify=False)

    # --- Réseau ---
    def run_dns_cloudflare(self):
        self.run_ps('Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | '
                    'Set-DnsClientServerAddress -ServerAddresses '
                    '("1.1.1.1","1.0.0.1"); Write-Host "DNS Cloudflare OK"',
                    "DNS Cloudflare")

    def run_dns_google(self):
        self.run_ps('Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | '
                    'Set-DnsClientServerAddress -ServerAddresses '
                    '("8.8.8.8","8.8.4.4"); Write-Host "DNS Google OK"',
                    "DNS Google")

    def run_dns_auto(self):
        self.run_ps('Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | '
                    'Set-DnsClientServerAddress -ResetServerAddresses; '
                    'Write-Host "DNS automatique restauré"', "DNS automatique")

    def run_autotuning(self):
        self.run_cmd("netsh int tcp set global autotuninglevel=disabled",
                     "Auto-tuning TCP")

    def run_tcpip(self):
        self.run_cmd("netsh int tcp set global ecncapability=disabled && "
                     "netsh int tcp set global dca=enabled", "TCP/IP QoS")

    def run_ipv6(self):
        if not self._confirm("Désactiver IPv6",
                "IPv6 sera désactivé sur tous les adaptateurs réseau.\n\n"
                "⚠  Cela peut perturber certains VPN ou services modernes.\n\n"
                "Continuer ?", danger=True):
            return
        self.run_ps('Get-NetAdapter | ForEach-Object { '
                    'Disable-NetAdapterBinding -Name $_.Name '
                    '-ComponentID ms_tcpip6 -EA SilentlyContinue }; '
                    'Write-Host "IPv6 desactive"', "IPv6")

    def run_nic_opt(self):
        self.run_ps('Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | '
                    'ForEach-Object { Set-NetAdapterAdvancedProperty '
                    '-Name $_.Name -RegistryKeyword "*InterruptModeration" '
                    '-RegistryValue 0 -EA SilentlyContinue }; '
                    'Write-Host "Adaptateur optimise"', "Adaptateur réseau")

    def run_net_reset(self):
        if not self._confirm("Réinitialiser la pile réseau",
                "La pile réseau Windows (TCP/IP + Winsock) va être "
                "réinitialisée.\n\n"
                "⚠  La connexion sera coupée et un REDÉMARRAGE sera "
                "nécessaire ensuite. Continuer ?", danger=True):
            return
        self.run_cmd("netsh int ip reset && netsh winsock reset && "
                     "ipconfig /flushdns", "Réinitialisation réseau")

    def run_ping(self):
        self.run_cmd("ping -n 8 1.1.1.1", "Test de ping — Cloudflare")

    def run_ipinfo(self):
        self.run_cmd("ipconfig /all", "Informations IP")

    # --- Confidentialité ---
    def run_telemetry(self):
        self.run_ps('sc stop DiagTrack; sc config DiagTrack start=disabled; '
                    'sc stop dmwappushservice; '
                    'sc config dmwappushservice start=disabled; '
                    'New-Item "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows'
                    '\\DataCollection" -Force -EA SilentlyContinue | Out-Null; '
                    'Set-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft'
                    '\\Windows\\DataCollection" -Name "AllowTelemetry" -Value 0; '
                    'Write-Host "Telemetrie desactivee"', "Télémétrie")

    def run_cortana(self):
        self.run_ps('New-Item "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows'
                    '\\Windows Search" -Force -EA SilentlyContinue | Out-Null; '
                    'Set-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft'
                    '\\Windows\\Windows Search" -Name "AllowCortana" -Value 0; '
                    'Write-Host "Cortana desactivee"', "Cortana")

    def run_ads(self):
        self.run_ps('$c="HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion'
                    '\\ContentDeliveryManager"; '
                    'Set-ItemProperty $c -Name "SubscribedContent-338389Enabled" -Value 0; '
                    'Set-ItemProperty $c -Name "SystemPaneSuggestionsEnabled" -Value 0; '
                    'Write-Host "Publicites desactivees"', "Publicités Windows")

    def run_activity(self):
        self.run_ps('New-Item "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows'
                    '\\System" -Force -EA SilentlyContinue | Out-Null; '
                    'Set-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft'
                    '\\Windows\\System" -Name "PublishUserActivities" -Value 0; '
                    'Write-Host "Activity History desactive"', "Activity History")

    def run_location(self):
        self.run_ps('Set-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows'
                    '\\CurrentVersion\\CapabilityAccessManager\\ConsentStore'
                    '\\location" -Name "Value" -Value "Deny"; '
                    'Write-Host "Localisation desactivee"', "Localisation")

    def run_diag(self):
        self.run_ps('Set-ItemProperty "HKCU:\\Software\\Microsoft\\Windows'
                    '\\CurrentVersion\\Privacy" -Name '
                    '"TailoredExperiencesWithDiagnosticDataEnabled" -Value 0; '
                    'Write-Host "Diagnostics desactives"', "Diagnostics & Feedback")

    def run_start_sugg(self):
        self.run_ps('$c="HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion'
                    '\\ContentDeliveryManager"; '
                    'Set-ItemProperty $c -Name "SubscribedContent-338393Enabled" -Value 0; '
                    'Set-ItemProperty $c -Name "SubscribedContent-353694Enabled" -Value 0; '
                    'Write-Host "Suggestions desactivees"', "Suggestions démarrage")

    def run_advertising_id(self):
        self.run_ps('New-Item "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion'
                    '\\AdvertisingInfo" -Force -EA SilentlyContinue | Out-Null; '
                    'Set-ItemProperty "HKCU:\\Software\\Microsoft\\Windows'
                    '\\CurrentVersion\\AdvertisingInfo" -Name "Enabled" -Value 0; '
                    'Write-Host "ID publicite desactive"', "ID de publicité")

    # ================================================================== #
    #  ACTIONS GROUPÉES                                                    #
    # ================================================================== #
    def _run_batch(self, steps, title, end_msg):
        def task():
            self.log(f"\n🚀  {title}\n")
            for cmd, label in steps:
                self._exec(cmd, label)
            self.log("\n" + "═"*60)
            self.log(f"✅  {end_msg}")
            self.log("═"*60 + "\n")
            self.set_status(f"✅  {end_msg}")
            try:
                self.root.bell()
            except:
                pass
            self.root.after(0, lambda: messagebox.showinfo("Terminé", end_msg))
        threading.Thread(target=task, daemon=True).start()

    def _optimize_catalog(self):
        """Catalogue des optimisations proposées dans la fenêtre de sélection.
        Renvoie une liste de tuples (libellé, commande, coché_par_défaut).
        Les commandes sont identiques à l'ancien « Tout optimiser »."""
        return [
            ("Réparer les fichiers système (SFC)", "sfc /scannow", True),
            ("Réparer l'image Windows (DISM)",
             "DISM /Online /Cleanup-Image /RestoreHealth", True),
            ("Vider les fichiers temporaires",
             'cmd /c "del /q /f /s %TEMP%\\* 2>nul"', True),
            ("Vider le cache DNS", "ipconfig /flushdns", True),
            ("Vider la Corbeille", self._ps("Clear-RecycleBin -Force"), True),
            ("Optimiser le disque C:", self._ps("Optimize-Volume -DriveLetter C"), True),
            ("Désactiver SysMain",
             "sc stop SysMain & sc config SysMain start=disabled", False),
            ("Désactiver l'hibernation", "powercfg /h off", False),
            ("Plan d'alimentation Haute Performance",
             "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", True),
            ("Activer le Game Mode",
             self._ps('Set-ItemProperty "HKCU:\\Software\\Microsoft\\GameBar" '
                      '-Name "AutoGameModeEnabled" -Value 1'), True),
            ("Activer HAGS (planification GPU)",
             self._ps('Set-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet'
                      '\\Control\\GraphicsDrivers" -Name "HwSchMode" -Value 2'), False),
            ("Désactiver l'accélération souris",
             self._ps('Set-ItemProperty "HKCU:\\Control Panel\\Mouse" '
                      '-Name "MouseSpeed" -Value "0"'), True),
            ("Priorité gaming (réactivité système)",
             self._ps('$p="HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'
                      '\\Multimedia\\SystemProfile"; Set-ItemProperty "$p" '
                      '-Name "SystemResponsiveness" -Value 0'), False),
            ("Désactiver l'auto-tuning TCP",
             "netsh int tcp set global autotuninglevel=disabled", False),
            ("Désactiver la télémétrie Windows",
             self._ps('sc stop DiagTrack; sc config DiagTrack start=disabled'), False),
            ("Mettre à jour les logiciels (winget)",
             "winget upgrade --all --silent --accept-source-agreements "
             "--accept-package-agreements", False),
        ]

    def run_all(self):
        """Ouvre une fenêtre de sélection (cases à cocher) avant de lancer,
        pour choisir les optimisations et éviter les clics malheureux."""
        catalog = self._optimize_catalog()

        win = tk.Toplevel(self.root)
        win.title("Choisir les optimisations à lancer")
        win.configure(bg=BG)
        win.geometry("660x660")
        win.minsize(520, 480)
        win.transient(self.root)
        try:
            win.grab_set()
        except Exception:
            pass

        tk.Label(win, text="⚙️  Optimisations à appliquer",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=ACCENT
                 ).pack(anchor=tk.W, padx=16, pady=(14, 2))
        tk.Label(win, text="Tout est coché par défaut. Décochez ce que vous "
                 "ne voulez pas appliquer, puis lancez.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED, justify=tk.LEFT
                 ).pack(anchor=tk.W, padx=16, pady=(0, 8))

        # Option point de restauration (en haut, cochée)
        rp_var = tk.BooleanVar(value=True)
        tk.Checkbutton(win,
                       text="🛡️  Créer un point de restauration avant de lancer "
                       "(recommandé)",
                       variable=rp_var, font=("Segoe UI", 9, "bold"),
                       bg=BG, fg=SUCCESS, selectcolor=BG3,
                       activebackground=BG, activeforeground=SUCCESS,
                       anchor=tk.W).pack(fill=tk.X, padx=16, pady=(0, 6))

        # Barre tout cocher / décocher
        bar = tk.Frame(win, bg=BG)
        bar.pack(fill=tk.X, padx=16)

        # Zone scrollable des cases
        container = tk.Frame(win, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"
        canvas.bind("<MouseWheel>", _wheel)

        var_list = []  # (BooleanVar, cmd, label)
        for label, cmd, default in catalog:
            v = tk.BooleanVar(value=default)
            var_list.append((v, cmd, label))
            cb = tk.Checkbutton(inner, text=label, variable=v,
                                font=("Segoe UI", 9), bg=CARD, fg=TEXT,
                                selectcolor=BG3, activebackground=CARD,
                                activeforeground=TEXT, anchor=tk.W,
                                wraplength=560, justify=tk.LEFT)
            cb.pack(fill=tk.X, padx=2, pady=2)
            cb.bind("<MouseWheel>", _wheel)

        def set_all(state):
            for v, _, _ in var_list:
                v.set(state)
        tk.Button(bar, text="Tout cocher", command=lambda: set_all(True),
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.LEFT, padx=(0, 4), pady=4)
        tk.Button(bar, text="Tout décocher", command=lambda: set_all(False),
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=8).pack(side=tk.LEFT, padx=4, pady=4)

        # Pied : lancer / annuler
        foot = tk.Frame(win, bg=BG)
        foot.pack(fill=tk.X, padx=16, pady=(4, 14))

        def launch():
            chosen = [(cmd, lbl) for v, cmd, lbl in var_list if v.get()]
            if not chosen:
                messagebox.showinfo("Optimisations",
                                    "Aucune optimisation sélectionnée.", parent=win)
                return
            create_rp = rp_var.get()
            msg = f"Lancer {len(chosen)} optimisation(s) sélectionnée(s) ?"
            if create_rp:
                msg += "\n\nUn point de restauration sera créé d'abord."
            msg += "\n⚠  Durée variable selon la sélection (jusqu'à ~20 min)."
            if not messagebox.askyesno("Confirmer le lancement", msg, parent=win):
                return
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            steps = []
            if create_rp:
                steps.append(
                    (self._ps('Checkpoint-Computer -Description "PC Optimizer" '
                              '-RestorePointType MODIFY_SETTINGS'),
                     "Point de restauration"))
            steps.extend(chosen)
            self._run_batch(steps, "OPTIMISATION (SÉLECTION)",
                            f"{len(chosen)} optimisation(s) terminée(s) — "
                            "Redémarrage recommandé")

        def cancel():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        tk.Button(foot, text="🚀  Lancer la sélection", command=launch,
                  font=("Segoe UI", 10, "bold"), bg=ACCENT2, fg="white",
                  activebackground="#ff8855", relief=tk.FLAT, cursor="hand2",
                  pady=10, padx=16).pack(side=tk.RIGHT)
        tk.Button(foot, text="Annuler", command=cancel,
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", pady=10, padx=16).pack(side=tk.RIGHT, padx=8)

    def run_clean_all(self):
        steps = [
            ('cmd /c "del /q /f /s %TEMP%\\* 2>nul & '
             'del /q /f /s C:\\Windows\\Temp\\* 2>nul"', "Temp"),
            ('cmd /c "del /q /f /s C:\\Windows\\Prefetch\\* 2>nul"', "Prefetch"),
            ('cmd /c "del /q /f /s %LocalAppData%\\Microsoft\\Windows'
             '\\Explorer\\thumbcache_*.db 2>nul"', "Miniatures"),
            ("ipconfig /flushdns", "Cache DNS"),
            (self._ps("Clear-RecycleBin -Force"), "Corbeille"),
            (self._ps("Optimize-Volume -DriveLetter C"), "Disque"),
        ]
        self._run_batch(steps, "NETTOYAGE COMPLET", "Nettoyage terminé")

    def run_privacy_all(self):
        steps = [
            (self._ps('sc stop DiagTrack; sc config DiagTrack start=disabled'),
             "Télémétrie"),
            (self._ps('New-Item "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows'
                      '\\Windows Search" -Force -EA SilentlyContinue | Out-Null; '
                      'Set-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft'
                      '\\Windows\\Windows Search" -Name "AllowCortana" -Value 0'),
             "Cortana"),
            (self._ps('$c="HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion'
                      '\\ContentDeliveryManager"; Set-ItemProperty $c '
                      '-Name "SystemPaneSuggestionsEnabled" -Value 0'), "Publicités"),
            (self._ps('New-Item "HKCU:\\Software\\Microsoft\\Windows'
                      '\\CurrentVersion\\AdvertisingInfo" -Force '
                      '-EA SilentlyContinue | Out-Null; Set-ItemProperty '
                      '"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion'
                      '\\AdvertisingInfo" -Name "Enabled" -Value 0'), "ID publicité"),
        ]
        self._run_batch(steps, "VERROUILLAGE CONFIDENTIALITÉ",
                        "Confidentialité renforcée")

    # ================================================================== #
    #  RAPPORT HTML                                                        #
    # ================================================================== #
    def generate_report(self):
        def task():
            self.set_status("⏳  Génération du rapport…")
            self.log("\n▶  Génération du rapport HTML…")
            try:
                def cim(cls, prop):
                    """Get-CimInstance — remplace wmic (déprécié)."""
                    try:
                        cmd = (f'powershell -NoProfile -Command '
                               f'"(Get-CimInstance {cls} | '
                               f'Select-Object -First 1 -ExpandProperty {prop})"')
                        r = subprocess.check_output(cmd, shell=True, text=True,
                                encoding="utf-8", errors="replace", timeout=15,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                        return r.strip() or "N/A"
                    except:
                        return "N/A"

                rows = {
                    "Système d'exploitation": platform.platform(),
                    "Nom du PC": platform.node(),
                    "Processeur": cim("Win32_Processor", "Name"),
                    "Carte graphique": cim("Win32_VideoController", "Name"),
                    "Carte mère": cim("Win32_BaseBoard", "Product"),
                    "BIOS": cim("Win32_BIOS", "SMBIOSBIOSVersion"),
                }
                if HAS_PSUTIL:
                    vm = psutil.virtual_memory()
                    du = psutil.disk_usage("C:\\")
                    rows["Mémoire RAM"] = f"{vm.total/(1024**3):.1f} Go " \
                        f"({vm.percent}% utilisée)"
                    rows["Disque C:"] = f"{du.total/(1024**3):.0f} Go " \
                        f"({du.free/(1024**3):.0f} Go libres)"
                    rows["Cœurs CPU"] = f"{psutil.cpu_count(logical=False)} " \
                        f"physiques / {psutil.cpu_count()} logiques"

                stamp = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
                table = "".join(
                    f"<tr><td class='k'>{k}</td><td>{v}</td></tr>"
                    for k, v in rows.items())
                html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Rapport PC Optimizer Pro</title>
<style>
body{{font-family:'Segoe UI',sans-serif;background:#00142b;color:#e6edf3;
margin:0;padding:40px}}
.box{{max-width:760px;margin:auto;background:#07243f;border-radius:14px;
padding:36px;border:1px solid #0c2e4e}}
h1{{color:#19d6f5;margin:0 0 4px}}
.sub{{color:#8b949e;margin-bottom:26px;font-size:14px}}
table{{width:100%;border-collapse:collapse}}
td{{padding:11px 14px;border-bottom:1px solid #0c2e4e;font-size:14px}}
.k{{color:#ff6b35;font-weight:600;width:240px}}
.foot{{margin-top:26px;color:#8b949e;font-size:12px;text-align:center}}
</style></head><body><div class="box">
<h1>⚡ Rapport Système</h1>
<div class="sub">Généré par PC Optimizer Pro — {stamp}</div>
<table>{table}</table>
<div class="foot">PC Optimizer Pro v{VERSION}</div>
</div></body></html>"""

                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if not os.path.isdir(desktop):
                    desktop = os.path.expanduser("~")
                path = os.path.join(desktop, "Rapport_PC_Optimizer.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
                self.log(f"✓  Rapport enregistré : {path}")
                self.write_log(f"Rapport généré : {path}")
                os.startfile(path)
                self.set_status("✓  Rapport généré sur le Bureau")
            except Exception as e:
                self.log(f"✗  Erreur rapport : {e}")
                self.set_status("✓  Prêt")
        threading.Thread(target=task, daemon=True).start()

    # ================================================================== #
    #  SAUVEGARDE / RESTAURATION (registre, services, plan d'alim)         #
    # ================================================================== #
    def _backups_dir(self):
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
               else os.path.dirname(os.path.abspath(__file__))
        d = os.path.join(base, "backups")
        os.makedirs(d, exist_ok=True)
        return d

    def _hive_const(self, name):
        return (winreg.HKEY_CURRENT_USER if name == "HKCU"
                else winreg.HKEY_LOCAL_MACHINE)

    def _reg_read_entry(self, hive, subkey, name):
        """Lit une valeur de registre. Renvoie un dict JSON-sérialisable."""
        access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        try:
            with winreg.OpenKey(self._hive_const(hive), subkey, 0, access) as k:
                data, typ = winreg.QueryValueEx(k, name)
            if isinstance(data, (int, str)):
                return {"existed": True, "type": int(typ), "data": data}
            # Type non géré (binaire, multi-chaînes) : noté mais non restauré
            return {"existed": True, "type": int(typ), "data": None,
                    "unsupported": True}
        except FileNotFoundError:
            return {"existed": False}
        except OSError:
            return {"existed": False}

    def _reg_restore_entry(self, hive, subkey, name, snap):
        """Restaure une valeur depuis le snapshot. Renvoie (ok: bool, msg: str)."""
        access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        try:
            if snap.get("existed"):
                if snap.get("unsupported") or snap.get("data") is None:
                    return (False, "type non géré")
                with winreg.CreateKeyEx(self._hive_const(hive), subkey, 0,
                                        access) as k:
                    winreg.SetValueEx(k, name, 0, int(snap["type"]), snap["data"])
                return (True, "restaurée")
            # La valeur n'existait pas avant la modification → on la supprime
            try:
                with winreg.OpenKey(self._hive_const(hive), subkey, 0, access) as k:
                    winreg.DeleteValue(k, name)
                return (True, "supprimée (absente à l'origine)")
            except FileNotFoundError:
                return (True, "déjà absente")
            except OSError:
                return (True, "déjà absente")
        except Exception as e:
            return (False, str(e))

    def _active_power_scheme(self):
        """GUID du plan d'alimentation actif (ou None)."""
        try:
            import re
            out = subprocess.check_output(
                "powercfg /getactivescheme", shell=True, text=True,
                encoding="utf-8", errors="replace", timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW)
            m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                          r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
            return m.group(1) if m else None
        except Exception:
            return None

    def create_backup(self):
        if not HAS_WINREG:
            self.log("✗  winreg indisponible — sauvegarde impossible.")
            return
        def task():
            self.set_status("⏳  Sauvegarde des réglages…")
            self.log("\n▶  Création d'une sauvegarde des réglages…")
            entries = []
            for hive, subkey, name in REG_BACKUP:
                snap = self._reg_read_entry(hive, subkey, name)
                snap.update({"hive": hive, "subkey": subkey, "name": name})
                entries.append(snap)
            power_guid = self._active_power_scheme()
            manifest = {
                "version": VERSION,
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "power_scheme": power_guid,
                "registry": entries,
            }
            try:
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                folder = os.path.join(self._backups_dir(), f"backup_{stamp}")
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, "manifest.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                present = sum(1 for e in entries if e.get("existed"))
                self.log(f"✓  Sauvegarde créée : {folder}")
                self.log(f"   {present} valeur(s) présente(s) sauvegardée(s) "
                         f"sur {len(entries)} suivie(s)"
                         + (f" — plan d'alim : {power_guid}" if power_guid else ""))
                self.write_log(f"Sauvegarde créée : {folder}")
                self.set_status("✓  Sauvegarde créée")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Sauvegarde",
                    f"Sauvegarde créée :\n{folder}\n\n"
                    f"{present} valeur(s) enregistrée(s)."))
            except Exception as e:
                self.log(f"✗  Échec de la sauvegarde : {e}")
                self.set_status("✓  Prêt")
        threading.Thread(target=task, daemon=True).start()

    def _list_backups(self):
        """Liste les sauvegardes (plus récente d'abord)."""
        try:
            d = self._backups_dir()
            items = [os.path.join(d, n) for n in os.listdir(d)
                     if n.startswith("backup_")
                     and os.path.isfile(os.path.join(d, n, "manifest.json"))]
            items.sort(reverse=True)
            return items
        except Exception:
            return []

    def restore_latest_backup(self):
        if not HAS_WINREG:
            self.log("✗  winreg indisponible — restauration impossible.")
            return
        backups = self._list_backups()
        if not backups:
            messagebox.showinfo("Restauration",
                "Aucune sauvegarde trouvée.\n\nCréez d'abord une sauvegarde.")
            return
        latest = backups[0]
        try:
            with open(os.path.join(latest, "manifest.json"), "r",
                      encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            messagebox.showerror("Restauration",
                f"Impossible de lire la sauvegarde :\n{e}")
            return
        created = manifest.get("created", "?")
        if not messagebox.askyesno("Restaurer la sauvegarde",
                f"Restaurer les réglages de la sauvegarde du {created} ?\n\n"
                "Les valeurs de registre et services suivis seront remis dans "
                "l'état sauvegardé. Un redémarrage peut être nécessaire.",
                icon="warning"):
            return
        def task():
            self.set_status("⏳  Restauration…")
            self.log(f"\n▶  Restauration de la sauvegarde du {created}…")
            ok_count = fail_count = 0
            for e in manifest.get("registry", []):
                done, msg = self._reg_restore_entry(
                    e.get("hive"), e.get("subkey"), e.get("name"), e)
                if done:
                    ok_count += 1
                else:
                    fail_count += 1
                    self.log(f"   ⚠  {e.get('hive')}\\…\\{e.get('name')} : {msg}")
            guid = manifest.get("power_scheme")
            if guid:
                try:
                    subprocess.run(f"powercfg /setactive {guid}", shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
                    self.log(f"   ✓  Plan d'alimentation restauré ({guid})")
                except Exception as ex:
                    self.log(f"   ⚠  Plan d'alimentation : {ex}")
            self.log(f"✓  Restauration terminée : {ok_count} valeur(s) traitée(s)"
                     + (f", {fail_count} échec(s)" if fail_count else ""))
            self.write_log(f"Restauration depuis {latest} "
                           f"({ok_count} ok, {fail_count} échec)")
            self.set_status("✓  Restauration terminée")
            self.root.after(0, lambda: messagebox.showinfo("Restauration",
                "Restauration terminée.\n\n"
                "Un redémarrage est recommandé pour que tous les changements "
                "(services notamment) prennent effet."))
        threading.Thread(target=task, daemon=True).start()

    # ================================================================== #
    #  MISE À JOUR AUTOMATIQUE (GitHub)                                    #
    # ================================================================== #
    def check_update(self, silent=False):
        def task():
            self.set_status("⏳  Vérification des mises à jour…")
            self.log("\n▶  Vérification des mises à jour…")
            try:
                req = urllib.request.Request(
                    API_URL, headers={"User-Agent": "PCOptimizerPro"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode("utf-8"))

                latest = data.get("tag_name", "0")
                exe_url = None
                for asset in data.get("assets", []):
                    if asset.get("name", "").lower().endswith(".exe"):
                        exe_url = asset.get("browser_download_url")
                        break

                if _version_tuple(latest) > _version_tuple(VERSION):
                    self.log(f"🆕  Nouvelle version disponible : {latest} "
                             f"(actuelle : {VERSION})")
                    if not exe_url:
                        self.log("⚠  Aucun fichier .exe trouvé dans la release.")
                        import webbrowser
                        webbrowser.open(data.get("html_url", ""))
                        return
                    notes = (data.get("body") or "").strip()[:280]
                    msg = (f"Version {latest} disponible "
                           f"(vous avez la {VERSION}).\n\n")
                    if notes:
                        msg += f"Nouveautés :\n{notes}\n\n"
                    msg += ("Télécharger et installer maintenant ?\n"
                            "L'application redémarrera automatiquement.")
                    if messagebox.askyesno("Mise à jour disponible", msg):
                        self.download_and_install(exe_url, latest)
                else:
                    self.log(f"✓  Vous avez la dernière version ({VERSION}).")
                    if not silent:
                        messagebox.showinfo("Mise à jour",
                            f"Vous êtes à jour (version {VERSION}).")
            except Exception as e:
                self.log(f"✗  Vérification impossible : {e}")
                if not silent:
                    messagebox.showwarning("Mise à jour",
                        f"Impossible de vérifier les mises à jour.\n\n{e}")
            self.set_status("✓  Prêt")
        threading.Thread(target=task, daemon=True).start()

    def download_and_install(self, url, version):
        def task():
            self.set_status("⏳  Téléchargement de la mise à jour…")
            self.log(f"▶  Téléchargement de la version {version}…")
            try:
                tmp_dir = tempfile.gettempdir()
                new_exe = os.path.join(tmp_dir, "PCOptimizerPro_new.exe")

                req = urllib.request.Request(
                    url, headers={"User-Agent": "PCOptimizerPro"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    done = 0
                    with open(new_exe, "wb") as f:
                        while True:
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            done += len(chunk)
                            if total:
                                pct = done / total * 100
                                self.set_status(f"⏳  Téléchargement… {pct:.0f}%")
                self.log("✓  Téléchargement terminé.")

                if not getattr(sys, "frozen", False):
                    self.log("ℹ  Mode développement (.py) — pas d'exe à remplacer.")
                    messagebox.showinfo("Mise à jour",
                        "En mode script (.py), le remplacement automatique "
                        f"est impossible.\n\nNouvel exe téléchargé ici :\n{new_exe}")
                    self.set_status("✓  Prêt")
                    return

                current_exe = sys.executable
                exe_name = os.path.basename(current_exe)

                relay = os.path.join(tmp_dir, "pco_update.bat")
                with open(relay, "w", encoding="utf-8") as f:
                    f.write(
                        "@echo off\r\n"
                        "chcp 65001 >nul\r\n"
                        "echo Installation de la mise a jour, veuillez patienter...\r\n"
                        ":wait\r\n"
                        f'tasklist /FI "IMAGENAME eq {exe_name}" 2>nul '
                        f'| find /I "{exe_name}" >nul\r\n'
                        "if not errorlevel 1 (\r\n"
                        "  timeout /t 1 /nobreak >nul\r\n"
                        "  goto wait\r\n"
                        ")\r\n"
                        "timeout /t 1 /nobreak >nul\r\n"
                        f'move /y "{new_exe}" "{current_exe}" >nul\r\n'
                        f'start "" "{current_exe}"\r\n'
                        'del "%~f0"\r\n'
                    )

                self.write_log(f"Mise à jour vers {version} — relais lancé")
                messagebox.showinfo("Mise à jour",
                    "Téléchargement terminé.\n\n"
                    "L'application va se fermer puis redémarrer "
                    "automatiquement avec la nouvelle version.")

                subprocess.Popen(["cmd", "/c", relay],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.monitoring = False
                self.root.after(300, self.root.destroy)

            except Exception as e:
                self.log(f"✗  Échec de la mise à jour : {e}")
                self.write_log(f"ERREUR mise à jour : {e}")
                self.set_status("✓  Prêt")
                messagebox.showerror("Mise à jour",
                    f"La mise à jour a échoué :\n\n{e}")
        threading.Thread(target=task, daemon=True).start()

    def open_log(self):
        try:
            if os.path.exists(self.log_path):
                os.startfile(self.log_path)
            else:
                self.log("ℹ  Aucun journal pour le moment.")
        except Exception as e:
            self.log(f"✗  {e}")

    # ================================================================== #
    #  ICÔNE BARRE DES TÂCHES (SYSTEM TRAY)                                #
    # ================================================================== #
    def _create_tray_image(self, color=(0, 212, 255, 255)):
        """Génère une icône éclair sur fond sombre. La couleur indique l'état."""
        img = Image.new("RGBA", (64, 64), (0, 20, 43, 255))
        draw = ImageDraw.Draw(img)
        pts = [(38, 6), (18, 34), (28, 34), (22, 58),
               (46, 28), (36, 28), (44, 6)]
        draw.polygon(pts, fill=color)
        return img

    def _start_minimized(self):
        """Cache la fenêtre au démarrage et notifie l'utilisateur."""
        self.root.withdraw()
        if self.tray_icon:
            try:
                self.tray_icon.notify(
                    "L'application continue en arrière-plan.",
                    "PC Optimizer Pro - Lancé"
                )
            except:
                pass

    def _check_alerts(self, cpu, ram, disk):
        """Change la couleur de l'icône et notifie selon la charge."""
        max_load = max(cpu, ram, disk)
        if max_load > 90:
            level = "critical"
        elif max_load > 70:
            level = "warning"
        else:
            level = "ok"
        if level != self.last_alert_level:
            colors = {
                "ok":       (0, 212, 255, 255),   # cyan
                "warning":  (255, 170, 0, 255),   # orange
                "critical": (255, 70, 70, 255),   # rouge
            }
            if self.tray_icon:
                try:
                    self.tray_icon.icon = self._create_tray_image(colors[level])
                except:
                    pass
            # Notification quand on franchit warning ou critical (cooldown 5 min)
            if level in ("warning", "critical") and \
               time.time() - self.last_alert_time > 300:
                self._notify_alert(level, cpu, ram, disk)
                self.last_alert_time = time.time()
        self.last_alert_level = level

    def _notify_alert(self, level, cpu, ram, disk):
        """Envoie une notification Windows."""
        if not self.tray_icon:
            return
        title = "Charge élevée" if level == "warning" else "Charge critique"
        msg = f"CPU: {cpu:.0f}%  RAM: {ram:.0f}%  Disque: {disk:.0f}%"
        try:
            self.tray_icon.notify(msg, title)
        except:
            pass

    # ----- HISTORIQUE 24h ----- #
    def _history_path(self):
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
               else os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "history.json")

    def _load_history(self):
        """Charge l'historique du fichier et filtre les entrées > 24h."""
        try:
            path = self._history_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
                cutoff = time.time() - 86400
                self.history = [e for e in self.history if e[0] >= cutoff]
        except:
            self.history = []

    def _save_history_entry(self, cpu, ram, disk):
        """Ajoute une mesure et sauve dans history.json."""
        try:
            self.history.append([time.time(), cpu, ram, disk])
            cutoff = time.time() - 86400
            self.history = [e for e in self.history if e[0] >= cutoff]
            if len(self.history) > 1500:
                self.history = self.history[-1500:]
            with open(self._history_path(), "w", encoding="utf-8") as f:
                json.dump(self.history, f)
            if hasattr(self, "history_canvas"):
                self.root.after(0, self.draw_history)
        except:
            pass

    def build_history(self):
        """Construit l'onglet Historique."""
        p = self.tab_history
        top = tk.Frame(p, bg=BG)
        top.pack(fill=tk.X, padx=16, pady=10)
        tk.Label(top, text="📈  Historique d'utilisation (jusqu'à 24h)",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=ACCENT
                 ).pack(side=tk.LEFT)
        tk.Button(top, text="🔄  Rafraîchir", command=self.draw_history,
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief=tk.FLAT,
                  cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=4)
        leg = tk.Frame(p, bg=BG)
        leg.pack(fill=tk.X, padx=16)
        for txt, col in [("● CPU", ACCENT), ("● Mémoire", ACCENT2),
                         ("● Disque", PURPLE)]:
            tk.Label(leg, text=txt, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=col).pack(side=tk.LEFT, padx=10)
        self.history_canvas = tk.Canvas(p, bg="#05080f", highlightthickness=0,
                                         height=420)
        self.history_canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)
        self.history_info = tk.Label(p, text="", font=("Segoe UI", 8),
                                      bg=BG, fg=MUTED)
        self.history_info.pack(anchor=tk.W, padx=16, pady=(0, 12))
        self.history_canvas.bind("<Configure>", lambda e: self.draw_history())
        self.draw_history()

    def draw_history(self):
        """Dessine les 3 courbes (CPU/RAM/Disque) sur 24h."""
        if not hasattr(self, "history_canvas"):
            return
        try:
            c = self.history_canvas
            c.delete("all")
            w = c.winfo_width() or 800
            h = c.winfo_height() or 400
            margin_l, margin_b = 40, 30
            graph_w = w - margin_l - 20
            graph_h = h - margin_b - 20
            origin_x = margin_l
            origin_y = h - margin_b
            for pct in (0, 25, 50, 75, 100):
                y = origin_y - (pct / 100) * graph_h
                c.create_line(origin_x, y, w - 20, y, fill=BG3, dash=(2, 4))
                c.create_text(margin_l - 8, y, text=f"{pct}%", fill=MUTED,
                              font=("Segoe UI", 7), anchor=tk.E)
            if len(self.history) < 2:
                c.create_text(w / 2, h / 2,
                              text="Pas assez de données pour afficher l'historique\n"
                                   "(une mesure est enregistrée toutes les 60 secondes)",
                              fill=MUTED, font=("Segoe UI", 9), justify=tk.CENTER)
                self.history_info.config(text="0 mesure")
                return
            t_min = self.history[0][0]
            t_max = self.history[-1][0]
            t_range = max(t_max - t_min, 1)
            for color, key_idx in [(ACCENT, 1), (ACCENT2, 2), (PURPLE, 3)]:
                pts = []
                for entry in self.history:
                    x = origin_x + (entry[0] - t_min) / t_range * graph_w
                    y = origin_y - (entry[key_idx] / 100) * graph_h
                    pts.extend([x, y])
                if len(pts) >= 4:
                    c.create_line(*pts, fill=color, width=2, smooth=True)
            for frac in (0, 0.5, 1):
                t = t_min + frac * t_range
                x = origin_x + frac * graph_w
                ts = datetime.datetime.fromtimestamp(t).strftime("%H:%M")
                c.create_text(x, origin_y + 12, text=ts, fill=MUTED,
                              font=("Segoe UI", 7), anchor=tk.N)
            duration_h = (t_max - t_min) / 3600
            self.history_info.config(
                text=f"{len(self.history)} mesures sur {duration_h:.1f} heures")
        except Exception:
            pass

    def open_settings(self):
        """Fenêtre de préférences : démarrage Windows, démarrage minimisé,
        comportement de la fermeture."""
        win = tk.Toplevel(self.root)
        win.title("Paramètres")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        try:
            win.grab_set()
        except Exception:
            pass
        try:
            self.root.update_idletasks()
            x = self.root.winfo_rootx() + 80
            y = self.root.winfo_rooty() + 80
            win.geometry(f"+{x}+{y}")
        except Exception:
            pass

        tk.Label(win, text="⚙️  Paramètres", font=("Segoe UI", 15, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor=tk.W, padx=24, pady=(20, 4))
        tk.Label(win, text="Les choix sont enregistrés automatiquement.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(
                 anchor=tk.W, padx=24, pady=(0, 14))

        card = tk.Frame(win, bg=CARD)
        card.pack(fill=tk.X, padx=24, pady=(0, 18))

        tray_ok = bool(self.tray_icon)

        var_startup = tk.BooleanVar(value=self._is_startup_enabled())

        def toggle_startup():
            if not self._set_startup_enabled(var_startup.get()):
                var_startup.set(self._is_startup_enabled())
                from tkinter import messagebox
                messagebox.showwarning(
                    "Démarrage Windows",
                    "Impossible de modifier le démarrage automatique "
                    "(registre inaccessible).", parent=win)
            else:
                self.set_status("✓  Démarrage Windows mis à jour")

        var_min = tk.BooleanVar(value=self.settings.get("start_minimized", False))

        def toggle_min():
            self.settings["start_minimized"] = bool(var_min.get())
            self.save_settings()
            self.set_status("✓  Préférence enregistrée")

        var_close = tk.BooleanVar(value=self.settings.get("close_to_tray", True))

        def toggle_close():
            self.settings["close_to_tray"] = bool(var_close.get())
            self.save_settings()
            self.set_status("✓  Préférence enregistrée")

        var_mintray = tk.BooleanVar(
            value=self.settings.get("minimize_to_tray", False))

        def toggle_mintray():
            self.settings["minimize_to_tray"] = bool(var_mintray.get())
            self.save_settings()
            self.set_status("✓  Préférence enregistrée")

        var_upd = tk.BooleanVar(
            value=self.settings.get("check_updates_on_start", False))

        def toggle_upd():
            self.settings["check_updates_on_start"] = bool(var_upd.get())
            self.save_settings()
            self.set_status("✓  Préférence enregistrée")

        def add_check(text, desc, var, cmd, enabled=True):
            cb = tk.Checkbutton(
                card, text=text, variable=var, command=cmd,
                font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT,
                activebackground=CARD, activeforeground=TEXT,
                selectcolor=BG3, anchor=tk.W, cursor="hand2",
                state=(tk.NORMAL if enabled else tk.DISABLED))
            cb.pack(anchor=tk.W, padx=18, pady=(14, 2))
            tk.Label(card, text=desc, font=("Segoe UI", 9), bg=CARD,
                     fg=MUTED, justify=tk.LEFT, wraplength=440, anchor=tk.W
                     ).pack(anchor=tk.W, padx=46, pady=(0, 6))

        add_check("Lancer au démarrage de Windows",
                  "Ouvre PC Optimizer automatiquement à l'ouverture de session."
                  + ("" if HAS_WINREG else "  (registre indisponible)"),
                  var_startup, toggle_startup, enabled=HAS_WINREG)

        add_check("Démarrer minimisé dans la zone de notification",
                  "Au lancement, l'application se réduit à côté de l'horloge au "
                  "lieu d'ouvrir sa fenêtre."
                  + ("" if tray_ok else "  (zone de notification indisponible)"),
                  var_min, toggle_min, enabled=tray_ok)

        add_check("Fermer la fenêtre la réduit (au lieu de quitter)",
                  "Le bouton ✕ réduit l'application dans la zone de notification "
                  "et elle continue en arrière-plan. Décochez pour que ✕ quitte "
                  "réellement l'application."
                  + ("" if tray_ok else "  (zone de notification indisponible)"),
                  var_close, toggle_close, enabled=tray_ok)

        add_check("Réduire dans la zone de notification (bouton «_»)",
                  "Le bouton « réduire » envoie l'application à côté de l'horloge "
                  "au lieu de la laisser dans la barre des tâches."
                  + ("" if tray_ok else "  (zone de notification indisponible)"),
                  var_mintray, toggle_mintray, enabled=tray_ok)

        add_check("Vérifier les mises à jour au démarrage",
                  "Au lancement, vérifie discrètement si une nouvelle version est "
                  "disponible sur GitHub (vous prévient seulement si c'est le cas).",
                  var_upd, toggle_upd, enabled=True)

        if getattr(sys, "frozen", False) is False:
            tk.Label(win, text="ℹ️  « Lancer au démarrage » est prévu pour la "
                     "version installée (.exe).", font=("Segoe UI", 8),
                     bg=BG, fg=WARNING, justify=tk.LEFT, wraplength=460
                     ).pack(anchor=tk.W, padx=24, pady=(0, 8))

        tk.Button(win, text="Fermer", command=win.destroy,
                  font=("Segoe UI", 9, "bold"), bg=ACCENT, fg=BG,
                  relief=tk.FLAT, cursor="hand2", padx=18, pady=4
                  ).pack(anchor=tk.E, padx=24, pady=(2, 20))

    def _tray_settings(self, icon=None, item=None):
        """Ouvre les paramètres depuis le tray (réaffiche la fenêtre)."""
        self.root.after(0, lambda: (self.root.deiconify(),
                                     self.root.lift(),
                                     self.open_settings()))

    def _setup_tray(self):
        """Crée l'icône du tray et lance son thread."""
        try:
            image = self._create_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("Ouvrir", self._tray_show, default=True),
                pystray.MenuItem("Optimisation rapide", self._tray_optimize),
                pystray.MenuItem("Nettoyage rapide", self._tray_clean),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Paramètres", self._tray_settings),
                pystray.MenuItem("Quitter", self._tray_quit),
            )
            self.tray_icon = pystray.Icon(
                "PCOptimizerPro", image,
                f"PC Optimizer Pro v{VERSION}", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            self.write_log(f"Tray init error: {e}")
            self.tray_icon = None

    def _on_window_close(self):
        """Croix : réduit au tray ou quitte, selon la préférence."""
        if self.tray_icon and self.settings.get("close_to_tray", True):
            self.root.withdraw()
        else:
            self._tray_quit()

    def _on_minimize_event(self, event):
        """Si l'option est active, le bouton « réduire » (_) envoie l'appli
        dans la zone de notification au lieu de la barre des tâches."""
        if event.widget is not self.root:
            return  # ignore les événements des widgets enfants
        if not (self.tray_icon and self.settings.get("minimize_to_tray", False)):
            return
        try:
            # state() == "iconic" = vraie réduction (pas un withdraw interne)
            if self.root.state() == "iconic":
                self.root.after(10, self.root.withdraw)
        except Exception:
            pass

    def _tray_show(self, icon=None, item=None):
        """Réaffiche la fenêtre depuis le tray."""
        self.root.after(0, lambda: (self.root.deiconify(),
                                     self.root.lift(),
                                     self.root.focus_force()))

    def _tray_optimize(self, icon=None, item=None):
        """Lance « Tout optimiser » depuis le tray (ouvre la fenêtre)."""
        self.root.after(0, lambda: (self.root.deiconify(), self.run_all()))

    def _tray_clean(self, icon=None, item=None):
        """Lance « Tout nettoyer » depuis le tray (ouvre la fenêtre)."""
        self.root.after(0, lambda: (self.root.deiconify(), self.run_clean_all()))

    def _tray_quit(self, icon=None, item=None):
        """Quitte définitivement l'application."""
        self.monitoring = False
        try:
            self.gpu_monitor.close()
        except Exception:
            pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        self.root.after(0, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    app = PCOptimizerPro(root)
    root.mainloop()