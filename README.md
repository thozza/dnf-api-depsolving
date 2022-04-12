# dnf-api-depsolving
Experiments with DNF API depsolving

## Usage

The `dnf-depsolving.py` script takes a `<scenario_name>.json` file with depsolving request as an input and depsolves it using every implementation variant and dumps the results for every variant into file `<scenario_name>-results-v<variant_version>.json`. Package lists in the dumped results are sorted to make it possible to generate reasonable diff.

Example usage:
```bash
./dnf-depsolving.py -r scenario-1.json
```

## Summary of the current state (Apr 2022)

* The `Sack` object used by DNF currently can not fetch the list of installed packages on the system from any other source than an RPM DB. The DNF team is experimenting with other ways how to fill it with data, but there is currently no other way. Reasons are mainly that the code treats installed packages in a special way and there may be corner cases when the whole thing blows up if the data are faked and not read from the RPM DB.
* If one resolves multiple transactions using DNF API, the list of packages provided in any way are always just an input for the depsolving (they specify a goal). These are never threated as if they were installed on the system. However we can workaround some corner cases with this (e.g. translate package groups to a list of packages filtered using excludes, etc.).
* One must use the same `dnf.Base` instance for depsolving multiple transactions if they want to reuse any package **objects** from the first transaction also for the second one. The reason is that the `dnf.Base` object may be keeping references to the returned package objects and the behavior when using them with a different new `dnf.Base` instance is undefined. **However if we do not reuse objects, then depsolving using a separate `dnf.Base` object may be OK.**

## Implementations

| Implementation | Pros | Cons |
| :------------: | ---- | ---- |
|V1| - 2nd transaction does not pull any unnecessary weak deps of packages from 1st transaction <br><br> - 2nd transaction does not pull in excluded optional packages from comps groups <br><br> - weak dependencies of the user-requested packages are installed (behavior consistent with DNF on the system) | - excludes from 1st transaction are applied to all following transactions and can not be installed at all |
|V2| - 2nd transaction does not pull any unnecessary weak deps of packages from 1st transaction <br><br> - 2nd transaction does not pull in excluded optional packages from comps groups <br><br> - weak dependencies of the user-requested packages are installed (behavior consistent with DNF on the system) | - excludes from 1st transaction are applied to all following transactions and can not be installed at all |
|V3| - 2nd transaction does not pull in excluded optional packages from comps groups <br><br> - package explicitly excluded in 1st transaction can be installed in the following transactions <br><br> - weak dependencies of the user-requested packages are installed (behavior consistent with DNF on the system) | - 2nd transaction pulls in previously excluded weak deps of packages from 1st transaction <br><br> - using separate `dnf.Base` object is **dangerous** |
|V4| - 2nd transaction does not pull in excluded optional packages from comps groups <br><br> - package explicitly excluded in 1st transaction can be installed in the following transactions <br><br> - weak dependencies of the user-requested packages are installed (behavior consistent with DNF on the system) | - 2nd transaction pulls in previously excluded weak deps of packages from 1st transaction |
|V5| - 2nd transaction does not pull any unnecessary weak deps of packages from 1st transaction <br><br> - 2nd transaction does not pull in excluded optional packages from comps groups <br><br> - package explicitly excluded in 1st transaction can be installed in the following transactions | - weak dependencies of the user-requested packages are not installed <br><br> - not installing weak dependencies of user-requested packages diverges from the default DNF behavior on the system |

### Implementation V1

* depsolves multiple transactions in a row using using the same dnf.Base object
* does not reset the goal
* does not reset excludes for following transactions
* does not turn off weak-dependencies

### Implementation V2

* depsolves multiple transactions in a row using the same dnf.Base object
* the Goal is reset before every depsolving
* the result from previous transaction is added to the goal as explicit list of packages to install
* does not reset excludes for following transactions
* does not turn off weak-dependencies

### Implementation V3

* in principle the same as V2, but uses **NEW** DNF base for each transaction, so does not need to reset the Goal

### Implementation V4

* same as V2, but in addition resets excludes after depsolving

### Implementation V5

* same as V2, but resets excludes after depsolving and don't install weak dependencies if adding installed pkgs 

### Weak excludes (RHEL-9 only)

* Using "weak excludes" - list of packages which won't be pulled into the transaction as weak dependencies, but if any package has a hard dependency on them, they'll get included.
* Available only on RHEL-9
* Not implemented by the script

## Test data (request)

* generated results are in the `results/` directory.

| Impl. | Scenario 1 | Scenario 2 | Scenario 3 | Scenario 4 | Scenario 5 | Scenario 6 |
| :---: | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |
|V1| - package with conditional dependency successfully pulled in by the 2nd transaction <br><br> - only requested package and its dependencies are pulled in by the 2nd transaction | **transaction error** | - 2nd transaction does not add any new packages on top of the 1st transaction | - 2nd transaction does not add any new packages on top of the 1st transaction | - `glibc-all-langpacks` not pulled in by the 2nd transaction | - no conflict observed, `fedora-release-cloud` successfully pulled in in 1st transaction |
|V2| - same as V1 | **transaction error** | - same as V1 | - same as V1 | - same as V1 | - same as V1 |
|V3| - package with conditional dependency successfully pulled in by the 2nd transaction <br><br> - **2nd transaction pulls in extra 20** packages compared to V1, which are not weak/hard dependencies of the requested package | - 2nd transaction successfully pulls in package excluded in 1st transaction <br><br> - 2nd transaction pulls in extra packages, which are not weak/hard dependencies of the requested package  | - **2nd transaction pulls in extra packages**, which are weak dependencies of packages from the 1st transaction | - **2nd transaction pulls in extra packages**, which are weak dependencies of packages from the 1st transaction | - `glibc-all-langpacks` not pulled in by the 2nd transaction <br><br> - **2nd transaction pulls in extra packages**, which are weak dependencies of packages from the 1st transaction | - no conflict observed, `fedora-release-cloud` successfully pulled in in 1st transaction <br><br> - **2nd transaction pulls in extra packages**, which are weak dependencies of packages from the 1st transaction |
|V4| - same as V3 | - same as V3 |  - same as V3 | - same as V3 | - same as V3 | - same as V3 |
|V5| - **2nd transaction pulls in 5 less packages** compared to V1, which are weak deps of the requested package | - 2nd transaction successfully pulls in package excluded in 1st transaction <br><br> - 2nd transaction does not pull in extra packages, which are not weak/hard dependencies of the requested package, but also does not pull weak dependencies of the explicitly requested package | - same as V1 | - same as V1 | - same as V1 | - same as V1 |

### Scenario 1

* Uses RHEL-9.0 RPMRepo snapshot
* Tests that it is possible to install user packages with conditional dependency on `selinux-policy`

<br>

* 1st transaction
  * package list with comps group
  * explicit list of excludes
* 2nd transaction
  * include `bind` package which has conditional dependency on `selinux-policy` such as `Requires(post): ((selinux-policy and selinux-policy-base) if (selinux-policy-targeted or selinux-policy-mls))`

### Scenario 2

* Uses RHEL-9.0 RPMRepo snapshot
* Tests that it is possible to install user packages, which are excluded in the base image package set.

<br>

* 1st transaction
  * package list with comps group
  * explicit list of excludes
* 2nd transaction
  * include package explicitly excluded in the 1st transaction

### Scenario 3

* Uses RHEL-9.0 RPMRepo snapshot
* Tests the depsolving behavior if the second transaction does not add any new packages.

<br>

* 1st transaction
  * package list with comps group, including `kernel` package
  * explicit list of excludes
* 2nd transaction
  * empty - no new packages added

### Scenario 4

* Uses RHEL-9.0 RPMRepo snapshot
* Tests the current depsolving as done by `osbuild-composer` for vanilla images. The Blueprint package set (2nd transaction) always contain the `kernel` package.

<br>

* 1st transaction
  * package list with comps group, including `kernel` package
  * explicit list of excludes
* 2nd transaction
  * include `kernel` package

### Scenario 5

* Uses RHEL-8.6 RPMRepo snapshot
* Tests the current depsolving as done by `osbuild-composer` for vanilla images. The Blueprint package set (2nd transaction) always contain the `kernel` package.
* Tests if `glibc-all-langpacks` package is pulled in (it should not be if there is `langpacks-en` in the 1st transaction).

<br>

* 1st transaction
  * package list with comps group, including `kernel` package and `langpacks-en`
  * explicit list of excludes
* 2nd transaction
  * include `kernel` package

### Scenario 6

* Uses Fedora 35 RPMRepo snapshot
* Tests the current depsolving as done by `osbuild-composer` for vanilla images. The Blueprint package set (2nd transaction) always contain the `kernel` package.
* Tests if the 2nd transaction pulls in conflicting `fedora-release-*` or `fedora-identity-*`. If it does, the 2nd transaction will fail due to conflict.

<br>

* 1st transaction
  * package list with comps group, including `kernel` package and `fedora-release-cloud` (from `@Fedora Cloud Server` comps group)
  * explicit list of excludes
* 2nd transaction
  * include `kernel` package

## Conclusion

* **V1** and **V2** implementations produce ideal results, but fail to install packages explicitly excluded in the default image package set.
* **V3** is dangerous due to use of new `dnf.Base` object for each transaction depsolving.
* **V4** produces reasonable results and solves all of the current `osbuild-composer` depsolving issues. However, if user customizations are applied or if composer keeps any packages in the Blueprint package set even for vanilla images, the resulting image will contain excluded weak dependencies of packages in the default image package set. The behavior (WRT weak dependencies installation) for user-requested packages is identical to the DNF behavior on the system.
* **V5** produces reasonable results and solves all of the current `osbuild-composer` depsolving issues. However, by not installing weak dependencies for user-requested packages, the behavior (WRT weak dependencies installation) differs from the DNF behavior on the system.

Realistically, only **V4** and **V5** versions can be used in all situations.

### Proposed solution

The main question is what is a bigger problem or which option is more acceptable:

1. Pulling unrelated weak dependencies to the image, in case package customization is applied to the image (in case we can guarantee empty BP package set for vanilla images).
2. Diverging from DNF behavior on the system when installing user-requested packages on the image (in a way that weak dependencies won't be installed).

Option 1. corresponds with **V4**.
Option 2. corresponds with **V5**.

### YOLO solution

There is an option to combine **V1** / **V2** with **V4** / **V5**. The reasoning for doing so could be that **V1** / **V2** produce ideal results, but fail to depsolve a transaction if the user requested package (or its dependency) are explicitly excluded by the default image package set. In such case, the `dnf-json` tool could fall-back to **V4** / **V5** if depsolving using **V1** / **V2** failed.

One can consider the scenario when user requests a package which is (or its dependency) excluded in the base image package set to be a corner case. However, there are no data on how common this scenario is.

#### Pros of this approach

* Using **V1** / **V2** provides better results for transactions that do not fail.
* Resulting images will be smaller, compared to **V4** and would behave consistently with the DNF on the system, compared to **V5**.

#### Cons of this approach

* Falling back to different approach and depsolving again slows down the overall dependency solving and increases the time to build an image.
* The difference in behavior (when weak dependencies are installed for user-requested packages and when not) could be confusing and not transparent to the end-user. Which could result in customer cases and overall confusion on the end user-side.
