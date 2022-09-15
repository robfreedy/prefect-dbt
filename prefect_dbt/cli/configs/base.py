"""Module containing models for base configs"""

import abc
from typing import Any, Dict, Optional, Tuple

from prefect.blocks.core import Block
from pydantic import Field, SecretBytes, SecretStr


class DbtConfigs(Block, abc.ABC):
    """
    Abstract class for other dbt Configs.

    Attributes:
        extras: Extra target configs' keywords, not yet added
            to prefect-dbt, but available in dbt; if there are
            duplicate keys between extras and TargetConfigs,
            an error will be raised.
    """

    extras: Optional[Dict[str, Any]] = None

    _include_fields: Optional[Tuple[str]] = None
    _exclude_fields: Tuple[str] = ("block_type_slug",)
    _nested_fields: Tuple[str] = ("extras",)

    def _populate_configs_json(
        self, configs_json: Dict[str, Any], dict_: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively populate configs_json.
        """
        for key, value in dict_.items():
            # must use exclude fields here because of nesting;
            # e.g. `CredentialsTargetConfigs` contains `Credentials`
            # and `block_type_slug` is inside the Credentials
            if key.startswith("_") or key in self._exclude_fields:
                continue

            # key needs to be rstripped because schema alias doesn't get used
            key = key.rstrip("_")
            if value is not None:
                if key in self._nested_fields:
                    configs_json = self._populate_configs_json(configs_json, value)
                else:
                    if key in configs_json.keys():
                        raise ValueError(
                            f"The keyword, {key}, has already been provided in "
                            f"TargetConfigs; remove duplicated keywords to continue"
                        )
                    if isinstance(value, (SecretStr, SecretBytes)):
                        value = value.get_secret_value()
                    configs_json[key] = value
        return configs_json

    def get_configs(self) -> Dict[str, Any]:
        """
        Returns the dbt configs, likely used eventually for writing to profiles.yml.

        Returns:
            A configs JSON.
        """
        include = None
        if self._include_fields:
            include = set(self._include_fields + self._nested_fields)

        # cannot use exclude here; see note in _populate_configs_json
        subset_dict = self.dict(include=include)
        return self._populate_configs_json({}, subset_dict)


class TargetConfigs(DbtConfigs):
    """
    Target configs contain credentials and
    settings, specific to the warehouse you're connecting to.
    To find valid keys, head to the [Available adapters](
    https://docs.getdbt.com/docs/available-adapters) page and
    click the desired adapter's "Profile Setup" hyperlink.

    Attributes:
        type: The name of the database warehouse
        schema: The schema that dbt will build objects into;
            in BigQuery, a schema is actually a dataset.
        threads: The number of threads representing the max number
            of paths through the graph dbt may work on at once.

    Examples:
        Load stored TargetConfigs:
        ```python
        from prefect_dbt.cli.configs import TargetConfigs

        dbt_cli_target_configs = TargetConfigs.load("BLOCK_NAME")
        ```
    """

    _block_type_name = "dbt CLI Target Configs"
    _logo_url = "https://images.ctfassets.net/gm98wzqotmnx/5zE9lxfzBHjw3tnEup4wWL/9a001902ed43a84c6c96d23b24622e19/dbt-bit_tm.png?h=250"  # noqa
    _include_fields = ("type", "schema_", "threads") + (
        DbtConfigs._include_fields or ()
    )

    type: str
    schema_: str = Field(alias="schema")
    threads: int = 4


class CredentialsTargetConfigs(TargetConfigs, abc.ABC):
    """
    Abstract class for target configs that use credentials.
    """

    _nested_fields = ("credentials",) + (TargetConfigs._nested_fields or ())


class GlobalConfigs(DbtConfigs):
    """
    Global configs control things like the visual output
    of logs, the manner in which dbt parses your project,
    and what to do when dbt finds a version mismatch
    or a failing model. Docs can be found [here](
    https://docs.getdbt.com/reference/global-configs).

    Attributes:
        send_anonymous_usage_stats: Whether usage stats are sent to dbt.
        use_colors: Colorize the output it prints in your terminal.
        partial_parse: When partial parsing is enabled, dbt will use an
            stored internal manifest to determine which files have been changed
            (if any) since it last parsed the project.
        printer_width: Length of characters before starting a new line.
        write_json: Determines whether dbt writes JSON artifacts to
            the target/ directory.
        warn_error: Whether to convert dbt warnings into errors.
        log_format: The LOG_FORMAT config specifies how dbt's logs should
            be formatted. If the value of this config is json, dbt will
            output fully structured logs in JSON format.
        debug: Whether to redirect dbt's debug logs to standard out.
        version_check: Whether to raise an error if a project's version
            is used with an incompatible dbt version.
        fail_fast: Make dbt exit immediately if a single resource fails to build.
        use_experimental_parser: Opt into the latest experimental version
            of the static parser.
        static_parser: Whether to use the [static parser](
            https://docs.getdbt.com/reference/parsing#static-parser).

    Examples:
        Load stored GlobalConfigs:
        ```python
        from prefect_dbt.cli.configs import GlobalConfigs

        dbt_cli_global_configs = GlobalConfigs.load("BLOCK_NAME")
        ```
    """

    _block_type_name = "dbt CLI Global Configs"
    _logo_url = "https://images.ctfassets.net/gm98wzqotmnx/5zE9lxfzBHjw3tnEup4wWL/9a001902ed43a84c6c96d23b24622e19/dbt-bit_tm.png?h=250"  # noqa
    _include_fields = (
        "send_anonymous_usage_stats",
        "use_colors",
        "partial_parse",
        "printer_width",
        "write_json",
        "warn_error",
        "log_format",
        "debug",
        "version_check",
        "fail_fast",
        "use_experimental_parser",
        "static_parser",
    )

    send_anonymous_usage_stats: Optional[bool] = None
    use_colors: Optional[bool] = None
    partial_parse: Optional[bool] = None
    printer_width: Optional[int] = None
    write_json: Optional[bool] = None
    warn_error: Optional[bool] = None
    log_format: Optional[bool] = None
    debug: Optional[bool] = None
    version_check: Optional[bool] = None
    fail_fast: Optional[bool] = None
    use_experimental_parser: Optional[bool] = None
    static_parser: Optional[bool] = None


class MissingExtrasRequireError(ImportError):
    def __init__(self, service, *args, **kwargs):
        msg = (
            f"To use {service.title()}TargetConfigs, "
            f'execute `pip install "prefect-dbt[{service.lower()}]"`'
        )
        super().__init__(msg, *args, **kwargs)
