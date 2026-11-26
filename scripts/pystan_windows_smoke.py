"""Test the installed PyStan client with spawn multiprocessing."""
import multiprocessing as mp


def main():
    import httpstan
    import stan
    print("httpstan:", httpstan.__version__, httpstan.__file__, flush=True)
    print("stan:", stan.__version__, stan.__file__, flush=True)
    model = stan.build("parameters {real y;} model {y ~ normal(0,1);}", data={}, random_seed=12345)
    fit = model.sample(num_chains=2, num_warmup=50, num_samples=30)
    print("draw shape:", fit["y"].shape, flush=True)
    assert fit["y"].shape[-1] == 60


if __name__ == "__main__":
    mp.freeze_support()
    main()
