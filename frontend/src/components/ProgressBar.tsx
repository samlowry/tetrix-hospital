import { FC } from 'react';
import { Metrics } from '../types';

interface Props {
    metrics: Metrics;
}

export const ProgressBar: React.FC<Props> = ({ metrics }) => {
    const healthPercentage = metrics.health;
    
    return (
        <div className="progress-container">
            <div className="progress-header">
                <h3>TETRIX Health</h3>
                <span>{metrics.holder_count} / 100,000 holders</span>
            </div>
            <div className="progress-bar">
                <div 
                    className="progress-fill"
                    style={{ width: `${healthPercentage}%` }}
                />
            </div>
            <div className="progress-stats">
                <span>Health: {healthPercentage.toFixed(1)}%</span>
                <span>Cap: {metrics.capitalization.toFixed(2)} TETRIX</span>
            </div>
        </div>
    );
}; 