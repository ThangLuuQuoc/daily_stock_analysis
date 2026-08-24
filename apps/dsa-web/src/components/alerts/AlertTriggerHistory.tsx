import type React from 'react';
import { Activity } from 'lucide-react';
import { Badge, Card, EmptyState, Loading } from '../common';
import type { AlertTriggerItem } from '../../types/alerts';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiLanguage } from '../../i18n/uiText';
import { uiToReportLanguage } from '../../utils/reportLanguage';
import { formatDateTime } from '../../utils/format';
import { getMarketPhaseSummaryLabel } from '../../utils/marketPhase';

const STATUS_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: { triggered: '已触发', skipped: '已跳过', degraded: '降级', failed: '失败' },
  en: { triggered: 'Triggered', skipped: 'Skipped', degraded: 'Degraded', failed: 'Failed' },
  vi: { triggered: 'Đã kích hoạt', skipped: 'Đã bỏ qua', degraded: 'Giảm cấp', failed: 'Thất bại' },
};

const HISTORY_TEXT: Record<UiLanguage, {
  cardTitle: string;
  cardSubtitle: string;
  loading: string;
  emptyTitle: string;
  emptyDescription: string;
  quality: string;
  colStatus: string;
  colPhaseQuality: string;
  colTarget: string;
  colObserved: string;
  colThreshold: string;
  colDataSource: string;
  colDataTime: string;
  colReason: string;
}> = {
  zh: {
    cardTitle: '触发历史',
    cardSubtitle: '评估记录',
    loading: '正在加载触发历史',
    emptyTitle: '暂无触发历史',
    emptyDescription: '后台评估会记录 triggered、skipped、degraded 和 failed 状态；正常未触发不会写入历史。',
    quality: '质量',
    colStatus: '状态',
    colPhaseQuality: '阶段 / 质量',
    colTarget: '目标',
    colObserved: '观察值',
    colThreshold: '阈值',
    colDataSource: '数据源',
    colDataTime: '数据时间',
    colReason: '原因',
  },
  en: {
    cardTitle: 'Trigger History',
    cardSubtitle: 'Evaluation records',
    loading: 'Loading trigger history',
    emptyTitle: 'No trigger history yet',
    emptyDescription: 'Background evaluation records triggered, skipped, degraded and failed states; normal non-triggers are not stored.',
    quality: 'Quality',
    colStatus: 'Status',
    colPhaseQuality: 'Phase / Quality',
    colTarget: 'Target',
    colObserved: 'Observed',
    colThreshold: 'Threshold',
    colDataSource: 'Data source',
    colDataTime: 'Data time',
    colReason: 'Reason',
  },
  vi: {
    cardTitle: 'Lịch sử kích hoạt',
    cardSubtitle: 'Bản ghi đánh giá',
    loading: 'Đang tải lịch sử kích hoạt',
    emptyTitle: 'Chưa có lịch sử kích hoạt',
    emptyDescription: 'Tiến trình đánh giá nền ghi lại các trạng thái đã kích hoạt, đã bỏ qua, giảm cấp và thất bại; trường hợp bình thường không kích hoạt sẽ không được lưu.',
    quality: 'Chất lượng',
    colStatus: 'Trạng thái',
    colPhaseQuality: 'Giai đoạn / Chất lượng',
    colTarget: 'Mục tiêu',
    colObserved: 'Giá trị quan sát',
    colThreshold: 'Ngưỡng',
    colDataSource: 'Nguồn dữ liệu',
    colDataTime: 'Thời điểm dữ liệu',
    colReason: 'Lý do',
  },
};

function statusVariant(status: string): 'success' | 'warning' | 'danger' | 'default' {
  if (status === 'triggered') return 'success';
  if (status === 'skipped' || status === 'degraded') return 'warning';
  if (status === 'failed') return 'danger';
  return 'default';
}

function formatNullable(value?: string | number | null): string {
  if (value === null || value === undefined || value === '') return '--';
  return String(value);
}

function renderPhaseQuality(trigger: AlertTriggerItem, language: UiLanguage): React.ReactNode {
  const phase = getMarketPhaseSummaryLabel(trigger.marketPhaseSummary, uiToReportLanguage(language));
  const quality = trigger.analysisContextPackOverview?.dataQuality?.level;
  const limitations = trigger.analysisContextPackOverview?.dataQuality?.limitations?.slice(0, 2) ?? [];
  if (!phase && !quality && limitations.length === 0) {
    return <span className="text-xs text-muted-text">--</span>;
  }
  return (
    <div className="space-y-1">
      {phase ? <Badge variant="default">{phase.replace('市场阶段: ', '').replace('市场阶段：', '').replace('Market phase: ', '')}</Badge> : null}
      {quality ? <div className="text-xs text-secondary-text">{HISTORY_TEXT[language].quality}：{quality}</div> : null}
      {limitations.length ? (
        <div className="max-w-[180px] text-xs text-muted-text">{limitations.join('；')}</div>
      ) : null}
    </div>
  );
}

interface AlertTriggerHistoryProps {
  triggers: AlertTriggerItem[];
  isLoading?: boolean;
}

export const AlertTriggerHistory: React.FC<AlertTriggerHistoryProps> = ({ triggers, isLoading = false }) => {
  const { language } = useUiLanguage();
  const text = HISTORY_TEXT[language];
  const statusLabel = STATUS_LABELS[language];
  return (
    <Card title={text.cardTitle} subtitle={text.cardSubtitle} variant="bordered" padding="md">
      {isLoading ? <Loading label={text.loading} /> : null}
      {!isLoading && triggers.length === 0 ? (
        <EmptyState
          icon={<Activity className="h-6 w-6" />}
          title={text.emptyTitle}
          description={text.emptyDescription}
        />
      ) : null}
      {!isLoading && triggers.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="border-b border-border/60 text-xs uppercase text-muted-text">
              <tr>
                <th className="px-3 py-2 font-medium">{text.colStatus}</th>
                <th className="px-3 py-2 font-medium">{text.colPhaseQuality}</th>
                <th className="px-3 py-2 font-medium">{text.colTarget}</th>
                <th className="px-3 py-2 font-medium">{text.colObserved}</th>
                <th className="px-3 py-2 font-medium">{text.colThreshold}</th>
                <th className="px-3 py-2 font-medium">{text.colDataSource}</th>
                <th className="px-3 py-2 font-medium">{text.colDataTime}</th>
                <th className="px-3 py-2 font-medium">{text.colReason}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {triggers.map((trigger) => (
                <tr key={trigger.id} className="align-top">
                  <td className="px-3 py-3">
                    <Badge variant={statusVariant(trigger.status)}>
                      {statusLabel[trigger.status] ?? trigger.status}
                    </Badge>
                  </td>
                  <td className="px-3 py-3">{renderPhaseQuality(trigger, language)}</td>
                  <td className="px-3 py-3 font-mono text-secondary-text">{trigger.target}</td>
                  <td className="px-3 py-3 text-secondary-text">{formatNullable(trigger.observedValue)}</td>
                  <td className="px-3 py-3 text-secondary-text">{formatNullable(trigger.threshold)}</td>
                  <td className="px-3 py-3 text-secondary-text">{formatNullable(trigger.dataSource)}</td>
                  <td className="px-3 py-3 text-xs text-secondary-text">
                    {formatDateTime(trigger.dataTimestamp ?? trigger.triggeredAt)}
                  </td>
                  <td className="px-3 py-3 text-secondary-text">
                    {trigger.reason || trigger.diagnostics || '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Card>
  );
};
