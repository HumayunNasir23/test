import logging

from sqlalchemy import func

from doosra.common.consts import IN_PROGRESS, SUCCESS, FAILED, CANCELLED, PENDING
from doosra.ibm.common.report_consts import (
    WINDOWS_BACKUP,
    SNAPSHOT,
    COS_EXPORT,
    QCOW2_CONVERSION,
    CUSTOM_IMAGE_CREATION,
    REPORT_MESSAGE,
    MAIN_STEPS_PATH,
    STAGE_STEPS_PATH,
    RESOURCES_ARRAY_PATH,
    RESOURCE_SUMMARY_PATH, VPC_KEY, RESOURCE_GROUP_KEY, CLUSTER_BACKUP, CLUSTER_PROVISIONING, CLUSTER_RESTORE,
)
from doosra.models import IBMTask, IBMInstanceTasks

from doosra import db as doosradb

LOGGER = logging.getLogger("report_utils.py")


class ReportUtils:
    """This class have query functions which updates report statuses and messages"""

    def get_migration_steps(self, image_location=None, data_migration=False, windows_backup=False):
        """
        This function generate and return volume migration steps.
        :return: volume migration dictionary.
        """
        volume_migration = {
            "volume_migration": {
                "title": "Volume migration steps",
                "status": PENDING,
                "message": "",
                "steps": {},
            }
        }
        volume_migration_steps = {}
        if image_location == IBMInstanceTasks.LOCATION_CLASSICAL_VSI:
            if windows_backup:
                volume_migration_steps.update(WINDOWS_BACKUP)
            """if all 4 steps are required"""
            volume_migration_steps.update(SNAPSHOT)
            volume_migration_steps.update(COS_EXPORT)
            volume_migration_steps.update(QCOW2_CONVERSION)
            volume_migration_steps.update(CUSTOM_IMAGE_CREATION)

        elif image_location == IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE:
            """if all steps except snapshot are required"""
            volume_migration_steps.update(COS_EXPORT)
            volume_migration_steps.update(QCOW2_CONVERSION)
            volume_migration_steps.update(CUSTOM_IMAGE_CREATION)

        elif image_location in [IBMInstanceTasks.LOCATION_COS_VHD, IBMInstanceTasks.LOCATION_COS_VMDK]:
            """if all steps except snapshot and export to cos are required"""
            volume_migration_steps.update(QCOW2_CONVERSION)
            volume_migration_steps.update(CUSTOM_IMAGE_CREATION)

        elif image_location == IBMInstanceTasks.LOCATION_COS_QCOW2:
            """if only custom image creation is required"""
            volume_migration_steps.update(CUSTOM_IMAGE_CREATION)

        """for secondary volume migration, currently two steps are mandatory."""
        if data_migration:
            volume_migration_steps.update(SNAPSHOT)
            volume_migration_steps.update(COS_EXPORT)

        volume_migration["volume_migration"]["steps"].update(volume_migration_steps)
        
        return (
            volume_migration
            if volume_migration["volume_migration"]["steps"]
            else None
        )

    def get_cluster_migration_steps(self):
        """
        This function generate and return workload migration steps.
        :return: workload migration dictionary.
        """
        
        cluster_migration = {
            "cluster_migration": {
                "title": "Cluster Migration steps",
                "status": PENDING,
                "message": "",
                "steps": {},
            }
        }
        cluster_migration_steps = {}

        cluster_migration_steps.update(CLUSTER_BACKUP)
        cluster_migration_steps.update(CLUSTER_PROVISIONING)
        cluster_migration_steps.update(CLUSTER_RESTORE)

        cluster_migration["cluster_migration"]["steps"].update(cluster_migration_steps)

        return (
            cluster_migration
            if cluster_migration["cluster_migration"]["steps"]
            else None
        )

    def search_query(self, task_id, status, path):
        """
        This function search a given status in JSON column.
        """
        result = (
            doosradb.session.query(
                func.JSON_SEARCH(IBMTask.report, "one", status, None, path,)
            )
            .filter(IBMTask.id == task_id)
            .first()[0]
        )
        doosradb.session.commit()
        return result if result is not None else False

    def report_setter(
        self,
        task_id,
        status,
        message,
        stage,
        resource_type,
        step_path,
        resource_path,
        main_status=IN_PROGRESS,
        resources_summary_status=IN_PROGRESS,
        stage_status=IN_PROGRESS,
    ):
        """This function sets status and message to the given resource, stage and overall report."""

        """This is to treat summary message as a resource message in case of vpc and resource group as they dont 
        have a summary status and message"""
        if resource_type not in {VPC_KEY, RESOURCE_GROUP_KEY}:
            summary_message = "{stage} {status}, please expand to see the details".format(
                        stage=stage.capitalize(), status=resources_summary_status.lower()
                    )
        else:
            summary_message = message

        doosradb.session.query(IBMTask).filter(IBMTask.id == task_id).update(
            {
                IBMTask.report: func.JSON_SET(
                    IBMTask.report,
                    "{resource_path}{steps_path}.status".format(
                        resource_path=resource_path, steps_path=step_path
                    ),
                    status,
                    "{resource_path}{steps_path}.message".format(
                        resource_path=resource_path, steps_path=step_path
                    ),
                    message,
                    "$.steps.{stage}.steps.{resource_type}.status".format(
                        stage=stage, resource_type=resource_type
                    ),
                    resources_summary_status,
                    "$.steps.{stage}.steps.{resource_type}.message".format(
                        stage=stage, resource_type=resource_type
                    ),
                    summary_message,
                    "$.steps.{stage}.status".format(stage=stage),
                    stage_status,
                    "$.steps.{stage}.message".format(stage=stage),
                    "{stage} {status}, please expand to see the details.".format(
                        stage=stage.capitalize(), status=stage_status.lower()
                    ),
                    "$.status",
                    main_status,
                    "$.message",
                    "{stage} {status}, please expand to see the details".format(
                        stage=stage.capitalize(), status=main_status.lower()
                    ),
                )
            },
            synchronize_session=False,
        )
        doosradb.session.commit()

    def cancel_pending_status(self, task_id, path):
        """
        This function sets cancel status to every pending operation if any operation fails and nothing is in progress.
        """
        if not self.search_query(task_id, IN_PROGRESS, path):
            if self.search_query(task_id, FAILED, path):
                doosradb.session.query(IBMTask).filter(IBMTask.id == task_id).update(
                    {IBMTask.report: func.REPLACE(IBMTask.report, PENDING, CANCELLED)},
                    synchronize_session=False,
                )
                doosradb.session.commit()
                LOGGER.info("All pending operations have been cancelled")

    def calculate_stage_and_report_status(self, task_id, path):
        """This function calculates stage and report status."""
        if not self.search_query(task_id, IN_PROGRESS, path):
            if not self.search_query(task_id, PENDING, path):
                if not self.search_query(task_id, CANCELLED, path):
                    return (
                        FAILED if self.search_query(task_id, FAILED, path) else SUCCESS
                    )
                else:
                    return FAILED

    def get_resource_path(self, task_id, resource_name, path):
        """
        This function finds and return resource path from an array.
        :param task_id:
        :param resource_name: resource to find.
        :param path: path to search the resource in.
        :return:
        """
        return (
            doosradb.session.query(
                func.JSON_UNQUOTE(
                    func.REPLACE(
                        func.JSON_SEARCH(
                            IBMTask.report, "one", resource_name, None, path,
                        ),
                        ".name",
                        "",
                    )
                )
            )
            .filter(IBMTask.id == task_id)
            .first()[0]
        )

    def calculate_resources_summary_status(self, task_id, path):
        """This function calculates resources summary status."""

        if not self.search_query(task_id, IN_PROGRESS, path):
            if not self.search_query(task_id, CANCELLED, path):
                return FAILED if self.search_query(task_id, FAILED, path) else SUCCESS
            else:
                if self.search_query(task_id, FAILED, path):
                    return FAILED

    def set_nested_status(self, task_id, resource_path):
        """This function sets failed status to any in progress status and cancel to any pending status in nested
        dictionary. """

        func_json_extract = func.JSON_EXTRACT(IBMTask.report, resource_path,)
        doosradb.session.query(IBMTask).filter(IBMTask.id == task_id).update(
            {
                IBMTask.report: func.REPLACE(
                    IBMTask.report,
                    func_json_extract,
                    func.REPLACE(
                        func.REPLACE(func_json_extract, PENDING, CANCELLED,),
                        IN_PROGRESS,
                        FAILED,
                    ),
                ),
            },
            synchronize_session=False,
        )
        doosradb.session.commit()

    def stop_reporting(self, task_id, message):
        """This function sets stopped status to any in progress and pending status in report in any unpredicted failure.
        """
        doosradb.session.query(IBMTask).filter(IBMTask.id == task_id).update(
            {
                IBMTask.report:
                func.JSON_SET(
                    func.REPLACE(
                        func.REPLACE(
                            IBMTask.report,
                            PENDING,
                            CANCELLED, ),
                        IN_PROGRESS,
                        FAILED,
                    ),
                    "$.status",
                    FAILED,
                    "$.message",
                    "Internal server error, please try again later."
                )
            },
            synchronize_session=False,
        )
        doosradb.session.commit()
        LOGGER.error("REPORTING HAS BEEN STOPPED DUE TO '{error}'".format(error=message))

    def update_reporting(
        self, task_id, resource_name, resource_type, stage, status, message="", path=""
    ):
        """This function manage query actions."""
        import timeit
        try:
            start = timeit.default_timer()
            resource_path = self.get_resource_path(
                task_id=task_id,
                resource_name=resource_name,
                path=RESOURCE_SUMMARY_PATH.format(stage=stage, resource_type=resource_type),
            )
            if resource_path:
                self.report_setter(
                    task_id=task_id,
                    status=status,
                    message=message,
                    stage=stage,
                    resource_type=resource_type,
                    resource_path=resource_path,
                    step_path=path,
                )

                if path and status == FAILED:
                    self.set_nested_status(task_id=task_id, resource_path=resource_path)

                if status != IN_PROGRESS:
                    """An exception for vpc and resource group because they will always be a single resource, and
                    they dont have a summary status and message"""
                    resources_summary_status = status
                    if resource_type not in {VPC_KEY, RESOURCE_GROUP_KEY}:
                        resources_summary_status = self.calculate_resources_summary_status(
                            task_id=task_id,
                            path=RESOURCES_ARRAY_PATH.format(
                                stage=stage, resource_type=resource_type
                            ),
                        )

                    if resources_summary_status:
                        self.report_setter(
                            task_id=task_id,
                            status=status,
                            message=message,
                            stage=stage,
                            resource_type=resource_type,
                            resource_path=resource_path,
                            step_path=path,
                            resources_summary_status=resources_summary_status,
                        )
                        # TODO: currently this function runs on every call because we dont know if there's any
                        #  dangling pending status which was not cancelled on resource failure, so find a
                        #  way to make it run on need.

                        self.cancel_pending_status(
                            task_id=task_id, path=STAGE_STEPS_PATH.format(stage=stage)
                        )

                        """This function is running to determine if every thing in a particular stage is completed.
                        So, the current stage status can be updated"""
                        stage_status = self.calculate_stage_and_report_status(
                            task_id=task_id, path=STAGE_STEPS_PATH.format(stage=stage)
                        )

                        if stage_status:
                            self.report_setter(
                                task_id=task_id,
                                status=status,
                                message=message,
                                stage=stage,
                                resource_type=resource_type,
                                resource_path=resource_path,
                                step_path=path,
                                resources_summary_status=resources_summary_status,
                                stage_status=stage_status,
                            )

                        """Same function is running to determine if every thing is completed in the report.
                         So, the overall status can be updated."""
                        main_status = self.calculate_stage_and_report_status(
                            task_id=task_id, path=MAIN_STEPS_PATH
                        )
                        if main_status:
                            self.report_setter(
                                task_id=task_id,
                                status=status,
                                message=message,
                                stage=stage,
                                resource_type=resource_type,
                                resource_path=resource_path,
                                step_path=path,
                                resources_summary_status=resources_summary_status,
                                stage_status=stage_status,
                                main_status=main_status,
                            )

            stop = timeit.default_timer()
            LOGGER.info(
                REPORT_MESSAGE.format(
                    status=status,
                    stage=stage,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    path=path,
                    message=message,
                    time=stop - start,
                )
            )
        except Exception as ex:
            self.stop_reporting(task_id, ex)
