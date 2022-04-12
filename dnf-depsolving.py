#!/usr/bin/python3

import argparse
import json
import os
import tempfile

import dnf


def create_DNF_base(repos, module_platform_id, persistdir, cachedir, arch, install_weak_deps=True):
    base = dnf.Base()

    base.conf.fastestmirror = True
    base.conf.zchunk = False
    base.conf.module_platform_id = module_platform_id
    base.conf.config_file_path = "/dev/null"
    base.conf.persistdir = persistdir
    base.conf.cachedir = cachedir
    base.conf.install_weak_deps = install_weak_deps
    base.conf.substitutions['arch'] = arch
    base.conf.substitutions['basearch'] = dnf.rpm.basearch(arch)

    for repo in repos:
        dnf_repo = dnf.repo.Repo(repo["id"], base.conf)
        dnf_repo.baseurl = repo["baseurl"]
        base.repos.add(dnf_repo)

    base.fill_sack(load_system_repo=False)

    return base


def depsolve_transactions_v1(request):
    """
    - depsolves multiple transactions in a row using using the same dnf.Base object
    - does not reset the goal
    - does not reset excludes for following transactions
    - does not turn off weak-dependencies
    """
    result = []

    with tempfile.TemporaryDirectory() as tempdir:
        persistent_dir = os.path.join(tempdir, "persistent")
        os.makedirs(persistent_dir)
        cache_dir = os.path.join(tempdir, "cache")
        os.makedirs(cache_dir)

        dnf_base = create_DNF_base(request["repos"], request["module_platform_id"], persistent_dir, cache_dir, request["arch"])

        for transaction in request["transactions"]:
            # depsolve the current transaction
            dnf_base.install_specs(transaction.get("package-specs"), transaction.get("exclude-specs"), reponame=transaction.get("repos"))
            dnf_base.resolve()

            pkgs = []

            for tsi in dnf_base.transaction:
                if tsi.action not in dnf.transaction.FORWARD_ACTIONS:
                    continue
                pkgs.append(tsi.pkg)
            
            result.append(pkgs)
    
    return result


def depsolve_transactions_v2(request):
    """
    - depsolves multiple transactions in a row using the same dnf.Base object
    - the Goal is reset before every depsolving
    - the result from previous transaction is added to the goal as explicit list of packages to install
    - does not reset excludes for following transactions
    - does not turn off weak-dependencies
    """
    result = []

    with tempfile.TemporaryDirectory() as tempdir:
        persistent_dir = os.path.join(tempdir, "persistent")
        os.makedirs(persistent_dir)
        cache_dir = os.path.join(tempdir, "cache")
        os.makedirs(cache_dir)

        dnf_base = create_DNF_base(request["repos"], request["module_platform_id"], persistent_dir, cache_dir, request["arch"])

        for transaction in request["transactions"]:
            # reset the goal every time before depsolving 
            dnf_base.reset(goal=True)

            # set the packages from the last transaction as installed
            installed_pkgs = []
            try:
                installed_pkgs = result[-1]
            except IndexError:
                pass
            for installed_pkg in installed_pkgs:
                dnf_base.package_install(installed_pkg, strict=True)

            # depsolve the current transaction
            dnf_base.install_specs(transaction.get("package-specs"), transaction.get("exclude-specs"), reponame=transaction.get("repos"))
            dnf_base.resolve()

            pkgs = []

            for tsi in dnf_base.transaction:
                if tsi.action not in dnf.transaction.FORWARD_ACTIONS:
                    continue
                pkgs.append(tsi.pkg)
            
            result.append(pkgs)
    
    return result


def depsolve_transactions_v3(request):
    """
    - in principle the same as V2, but uses NEW! DNF base for each transaction, so does not need to reset the Goal
    """
    result = []

    for transaction in request["transactions"]:
        with tempfile.TemporaryDirectory() as tempdir:
            persistent_dir = os.path.join(tempdir, "persistent")
            os.makedirs(persistent_dir)
            cache_dir = os.path.join(tempdir, "cache")
            os.makedirs(cache_dir)

            dnf_base = create_DNF_base(request["repos"], request["module_platform_id"], persistent_dir, cache_dir, request["arch"])

            # set the packages from the last transaction as installed
            installed_pkgs = []
            try:
                installed_pkgs = result[-1]
            except IndexError:
                pass
            for installed_pkg in installed_pkgs:
                dnf_base.package_install(installed_pkg, strict=True)

            # depsolve the current transaction
            dnf_base.install_specs(transaction.get("package-specs"), transaction.get("exclude-specs"), reponame=transaction.get("repos"))
            dnf_base.resolve()

            pkgs = []

            for tsi in dnf_base.transaction:
                if tsi.action not in dnf.transaction.FORWARD_ACTIONS:
                    continue
                pkgs.append(tsi.pkg)
            
            result.append(pkgs)
    
    return result


def depsolve_transactions_v4(request):
    """
    - Same as V2, but resets excludes after depsolving
    """
    result = []

    with tempfile.TemporaryDirectory() as tempdir:
        persistent_dir = os.path.join(tempdir, "persistent")
        os.makedirs(persistent_dir)
        cache_dir = os.path.join(tempdir, "cache")
        os.makedirs(cache_dir)

        dnf_base = create_DNF_base(request["repos"], request["module_platform_id"], persistent_dir, cache_dir, request["arch"])

        for transaction in request["transactions"]:
            # reset the goal every time before depsolving 
            dnf_base.reset(goal=True)
            dnf_base.sack.reset_excludes()

            # set the packages from the last transaction as installed
            installed_pkgs = []
            try:
                installed_pkgs = result[-1]
            except IndexError:
                pass
            for installed_pkg in installed_pkgs:
                dnf_base.package_install(installed_pkg, strict=True)

            # depsolve the current transaction
            dnf_base.install_specs(transaction.get("package-specs"), transaction.get("exclude-specs"), reponame=transaction.get("repos"))
            dnf_base.resolve()

            pkgs = []

            for tsi in dnf_base.transaction:
                if tsi.action not in dnf.transaction.FORWARD_ACTIONS:
                    continue
                pkgs.append(tsi.pkg)
            
            result.append(pkgs)
    
    return result


def depsolve_transactions_v5(request):
    """
    - Same as V2, but resets excludes after depsolving and don't install weak-deps if adding installed pkgs 
    """
    result = []

    with tempfile.TemporaryDirectory() as tempdir:
        persistent_dir = os.path.join(tempdir, "persistent")
        os.makedirs(persistent_dir)
        cache_dir = os.path.join(tempdir, "cache")
        os.makedirs(cache_dir)

        dnf_base = create_DNF_base(request["repos"], request["module_platform_id"], persistent_dir, cache_dir, request["arch"])

        for transaction in request["transactions"]:
            # reset the goal every time before depsolving 
            dnf_base.reset(goal=True)
            dnf_base.sack.reset_excludes()

            # set the packages from the last transaction as installed
            installed_pkgs = []
            try:
                installed_pkgs = result[-1]
            except IndexError:
                pass
            else:
                # don't install weak-deps for transactions after the 1st transaction
                dnf_base.conf.install_weak_deps=False
            for installed_pkg in installed_pkgs:
                dnf_base.package_install(installed_pkg, strict=True)

            # depsolve the current transaction
            dnf_base.install_specs(transaction.get("package-specs"), transaction.get("exclude-specs"), reponame=transaction.get("repos"))
            dnf_base.resolve()

            pkgs = []

            for tsi in dnf_base.transaction:
                if tsi.action not in dnf.transaction.FORWARD_ACTIONS:
                    continue
                pkgs.append(tsi.pkg)
            
            result.append(pkgs)
    
    return result


def load_request(path):
    with open(path) as f:
        request = json.load(f)
        return request


def dump_results(path, results):
    dump_data = {}

    for idx, result in enumerate(results):
        d = {}
        d["pkgs_count"] = len(result)
        # sort the result to make it easier to diff resulting files
        d["pkgs"] = [f"{p.name}-{p.version}.{p.release}" for p in sorted(result)]
        if idx > 0:
            diff = set(result)-set.union(*[set(t) for t in results[:idx]])
            # sort the result to make it easier to diff resulting files
            d["added_from_previous"] = [f"{p.name}-{p.version}.{p.release}" for p in sorted(diff)]

        dump_data[idx] = d

    with open(path, "w") as f:
        json.dump(dump_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Test depsolving using DNF API")
    parser.add_argument(
        "-r", "--request",
        action="store",
        type=os.path.abspath,
        required=True,
        metavar="FILE",
        help="path to a JSON file with the request to depsolve"
    )
    options = parser.parse_args()

    req_file_path = options.request
    req_file_root = os.path.splitext(os.path.basename(req_file_path))[0]
    request = load_request(req_file_path)

    depsolving_versions = {
        "v1": depsolve_transactions_v1,
        "v2": depsolve_transactions_v2,
        "v3": depsolve_transactions_v3,
        "v4": depsolve_transactions_v4,
        "v5": depsolve_transactions_v5,
    }

    for version_name, function in depsolving_versions.items():
        print(f"Testing depsolving implementation {version_name}")

        try:
            results = function(request)
        except (dnf.exceptions.DepsolveError, dnf.exceptions.MarkingErrors) as e:
            print(e)
            continue

        dump_results(os.path.join(os.getcwd(), f"{req_file_root}-results-{version_name}.json"), results)


if __name__ == "__main__":
    main()
