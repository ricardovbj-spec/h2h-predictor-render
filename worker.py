
import time
from update_csvs import atualizar_csvs_via_sofascore

INTERVALO = 60 * 60 * 48


def main():
    while True:
        print("🔄 Iniciando atualização automática dos CSVs via SofaScore...")
        try:
            atualizar_csvs_via_sofascore()
            print("✅ Atualização concluída com sucesso!")
        except Exception as e:
            print("❌ Erro durante atualização:", repr(e))

        print(f"⏳ Aguardando {INTERVALO/3600:.0f} horas para próxima atualização...")
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
