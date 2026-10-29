"""``python -m libretime_shared.compat._probe`` must run (stage B bridge test)."""

if __name__ == "__main__":
    print(__spec__.name if __spec__ else "no-spec")
