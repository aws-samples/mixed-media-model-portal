from aws_cdk import CfnOutput, Stack
import aws_cdk.aws_ec2 as ec2
from constructs import Construct

class CdkVpcStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc(self, "HpcBlogVpc",
                           max_azs=6,
                           ip_addresses=ec2.IpAddresses.cidr("10.10.0.0/16"),
                           subnet_configuration=[ec2.SubnetConfiguration(
                               subnet_type=ec2.SubnetType.PUBLIC,
                               name="Public",
                               cidr_mask=24
                           ), ec2.SubnetConfiguration(
                               subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                               name="Private",
                               cidr_mask=24
                           )
                           ],
                           nat_gateways=1,
                           )
        CfnOutput(self, "Output",
                       value=self.vpc.vpc_id)