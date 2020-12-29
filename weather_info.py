from settings import DEFAULT_N_DAYS


class WeatherInfo:
    """
    coords = (longitude, latitude) user coords
    services = [s1, s2, ...] weather serviced to aggregate
    n_days = forecast period
    """

    def __init__(self, coords, services, n_days=DEFAULT_N_DAYS):
        self.coords = coords
        self.services = [s() for s in services]
        self.n_days = n_days

    def get_result(self):
        results = {}

        for s in self.services:
            r = s.get_info(self.coords, self.n_days)
            for k in r:
                if k in results:
                    results[k] += r[k]
                else:
                    results[k] = r[k]

        for k in results:
            results[k] /= len(self.services)

        return results
