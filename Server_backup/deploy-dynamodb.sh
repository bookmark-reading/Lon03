#!/bin/bash

# DynamoDB Deployment Script for Reading Assistant
# This script deploys the DynamoDB table using CloudFormation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="${STACK_NAME:-reading-assistant-dynamodb}"
TABLE_NAME="${TABLE_NAME:-ReadingSessions}"
REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
TTL_DAYS="${TTL_DAYS:-30}"
BILLING_MODE="${BILLING_MODE:-PAY_PER_REQUEST}"
ENABLE_PITR="${ENABLE_PITR:-true}"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    print_success "AWS CLI found"
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    fi
    print_success "AWS credentials configured"
    
    # Check CloudFormation template
    if [ ! -f "cloudformation-dynamodb.yaml" ]; then
        print_error "CloudFormation template not found: cloudformation-dynamodb.yaml"
        exit 1
    fi
    print_success "CloudFormation template found"
    
    echo ""
}

validate_template() {
    print_header "Validating CloudFormation Template"
    
    if aws cloudformation validate-template \
        --template-body file://cloudformation-dynamodb.yaml \
        --region "$REGION" &> /dev/null; then
        print_success "Template is valid"
    else
        print_error "Template validation failed"
        exit 1
    fi
    
    echo ""
}

check_stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" &> /dev/null
}

deploy_stack() {
    print_header "Deploying DynamoDB Stack"
    
    print_info "Stack Name: $STACK_NAME"
    print_info "Table Name: $TABLE_NAME"
    print_info "Region: $REGION"
    print_info "Environment: $ENVIRONMENT"
    print_info "TTL Days: $TTL_DAYS"
    print_info "Billing Mode: $BILLING_MODE"
    print_info "Point-in-Time Recovery: $ENABLE_PITR"
    echo ""
    
    # Check if stack exists
    if check_stack_exists; then
        print_warning "Stack already exists. Updating..."
        OPERATION="update-stack"
    else
        print_info "Creating new stack..."
        OPERATION="create-stack"
    fi
    
    # Deploy stack
    aws cloudformation "$OPERATION" \
        --stack-name "$STACK_NAME" \
        --template-body file://cloudformation-dynamodb.yaml \
        --parameters \
            ParameterKey=TableName,ParameterValue="$TABLE_NAME" \
            ParameterKey=TTLDays,ParameterValue="$TTL_DAYS" \
            ParameterKey=BillingMode,ParameterValue="$BILLING_MODE" \
            ParameterKey=EnablePointInTimeRecovery,ParameterValue="$ENABLE_PITR" \
            ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$REGION" \
        --tags \
            Key=Project,Value=ReadingAssistant \
            Key=Environment,Value="$ENVIRONMENT" \
            Key=ManagedBy,Value=CloudFormation
    
    print_success "Stack deployment initiated"
    echo ""
}

wait_for_stack() {
    print_header "Waiting for Stack Completion"
    
    if check_stack_exists; then
        STACK_STATUS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'Stacks[0].StackStatus' \
            --output text)
        
        if [[ "$STACK_STATUS" == *"IN_PROGRESS"* ]]; then
            print_info "Waiting for stack to complete..."
            
            aws cloudformation wait stack-create-complete \
                --stack-name "$STACK_NAME" \
                --region "$REGION" 2>/dev/null || \
            aws cloudformation wait stack-update-complete \
                --stack-name "$STACK_NAME" \
                --region "$REGION" 2>/dev/null
            
            print_success "Stack deployment completed"
        else
            print_success "Stack is already in final state: $STACK_STATUS"
        fi
    fi
    
    echo ""
}

get_outputs() {
    print_header "Stack Outputs"
    
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    echo ""
}

create_env_file() {
    print_header "Creating Environment File"
    
    # Get outputs
    TABLE_NAME_OUTPUT=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`TableName`].OutputValue' \
        --output text)
    
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationRoleArn`].OutputValue' \
        --output text)
    
    BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`AudioBucketName`].OutputValue' \
        --output text)
    
    # Create .env file
    cat > .env.dynamodb << EOF
# DynamoDB Configuration
DYNAMODB_TABLE_NAME=$TABLE_NAME_OUTPUT
DYNAMODB_REGION=$REGION
ENABLE_DYNAMODB_PERSISTENCE=true

# Optional: S3 Audio Storage
S3_AUDIO_BUCKET=$BUCKET_NAME
STORE_AUDIO_IN_S3=false

# Optional: IAM Role (for EC2/ECS)
AWS_ROLE_ARN=$ROLE_ARN

# DynamoDB Settings
DYNAMODB_BATCH_SIZE=25
DYNAMODB_BATCH_INTERVAL=5
DYNAMODB_TTL_DAYS=$TTL_DAYS
EOF
    
    print_success "Environment file created: .env.dynamodb"
    print_info "Add these variables to your .env file or export them"
    echo ""
    cat .env.dynamodb
    echo ""
}

test_connection() {
    print_header "Testing DynamoDB Connection"
    
    TABLE_NAME_OUTPUT=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`TableName`].OutputValue' \
        --output text)
    
    if aws dynamodb describe-table \
        --table-name "$TABLE_NAME_OUTPUT" \
        --region "$REGION" &> /dev/null; then
        print_success "Successfully connected to DynamoDB table"
        
        # Get table info
        ITEM_COUNT=$(aws dynamodb describe-table \
            --table-name "$TABLE_NAME_OUTPUT" \
            --region "$REGION" \
            --query 'Table.ItemCount' \
            --output text)
        
        TABLE_SIZE=$(aws dynamodb describe-table \
            --table-name "$TABLE_NAME_OUTPUT" \
            --region "$REGION" \
            --query 'Table.TableSizeBytes' \
            --output text)
        
        print_info "Item Count: $ITEM_COUNT"
        print_info "Table Size: $TABLE_SIZE bytes"
    else
        print_error "Failed to connect to DynamoDB table"
        exit 1
    fi
    
    echo ""
}

print_next_steps() {
    print_header "Next Steps"
    
    echo "1. Update your .env file with the variables from .env.dynamodb"
    echo "2. Install Python dependencies:"
    echo "   pip install boto3 aioboto3"
    echo ""
    echo "3. Implement the persistence layer:"
    echo "   - Create dynamodb_persistence.py"
    echo "   - Create dynamodb_models.py"
    echo "   - Update audio_buffer_manager.py"
    echo ""
    echo "4. Test locally with DynamoDB:"
    echo "   python app.py"
    echo ""
    echo "5. Monitor in AWS Console:"
    echo "   https://console.aws.amazon.com/dynamodb/home?region=$REGION#tables:selected=$TABLE_NAME_OUTPUT"
    echo ""
}

# Main execution
main() {
    print_header "DynamoDB Deployment for Reading Assistant"
    echo ""
    
    check_prerequisites
    validate_template
    deploy_stack
    wait_for_stack
    get_outputs
    create_env_file
    test_connection
    print_next_steps
    
    print_success "Deployment completed successfully!"
}

# Run main function
main
