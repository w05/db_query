/** Post-query AI assistant prompt: ask whether to export results. */

import React from "react";
import { Alert, Button, Space, Typography } from "antd";
import { DownloadOutlined, RobotOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface ExportPromptProps {
  rowCount: number;
  onExportCsv: () => void;
  onExportJson: () => void;
  onDismiss: () => void;
  onNeverAsk: () => void;
}

export const ExportPrompt: React.FC<ExportPromptProps> = ({
  rowCount,
  onExportCsv,
  onExportJson,
  onDismiss,
  onNeverAsk,
}) => {
  return (
    <Alert
      type="info"
      showIcon
      icon={<RobotOutlined />}
      style={{ marginBottom: 16, borderWidth: 2, borderColor: "#000000" }}
      message={
        <Text strong style={{ fontSize: 13 }}>
          AI 助手
        </Text>
      }
      description={
        <div>
          <Paragraph style={{ marginBottom: 8, fontSize: 14 }}>
            查询完成，共 <Text strong>{rowCount.toLocaleString()}</Text>{" "}
            行。需要将这次查询结果导出为 CSV 或 JSON 文件吗？
          </Paragraph>
          <Space wrap>
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              onClick={onExportCsv}
              style={{ fontWeight: 700 }}
            >
              导出 CSV
            </Button>
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={onExportJson}
              style={{ fontWeight: 700 }}
            >
              导出 JSON
            </Button>
            <Button size="small" onClick={onDismiss}>
              不用了
            </Button>
            <Button type="link" size="small" onClick={onNeverAsk}>
              不再询问
            </Button>
          </Space>
        </div>
      }
      closable
      onClose={onDismiss}
    />
  );
};
